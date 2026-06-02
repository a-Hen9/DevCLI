"""Model Gateway for LLM communication with token tracking and model routing."""
import asyncio
import json
from collections.abc import AsyncIterator

import httpx

from devcli.config import DASHSCOPE_BASE_URL, DEFAULT_MODEL, MAX_RETRIES, MODEL_ROUTING, RETRY_DELAY


class ModelError(Exception):
    pass


class RateLimitError(ModelError):
    pass


class ConfigurationError(ModelError):
    pass


class ModelGateway:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or None
        self.default_model = model or DEFAULT_MODEL
        self.base_url = DASHSCOPE_BASE_URL.rstrip("/")
        self._usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def _get_api_key(self) -> str:
        import os
        key = self.api_key or os.getenv("DASHSCOPE_API_KEY")
        if not key:
            raise ConfigurationError("API key not configured. Set DASHSCOPE_API_KEY.")
        return key

    def route_model(self, task_type: str) -> str:
        return MODEL_ROUTING.get(task_type, self.default_model)

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        stream: bool = True,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str] | str:
        api_key = self._get_api_key()
        model_name = model or self.default_model
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        if stream:
            return self._stream_chat(headers, payload)
        else:
            return await self._non_stream_chat(headers, payload)

    async def _stream_chat(
        self, headers: dict, payload: dict
    ) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                if response.status_code == 429:
                    raise RateLimitError("Rate limited by the API.")
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

    async def _non_stream_chat(self, headers: dict, payload: dict) -> str:
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    if response.status_code == 429:
                        raise RateLimitError("Rate limited by the API.")
                    response.raise_for_status()
                    data = response.json()
                    usage = data.get("usage", {})
                    if usage:
                        self._usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
                        self._usage["completion_tokens"] += usage.get("completion_tokens", 0)
                        self._usage["total_tokens"] += usage.get("total_tokens", 0)
                    return data["choices"][0]["message"]["content"]
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                if attempt == MAX_RETRIES - 1:
                    raise ModelError(f"API request failed after {MAX_RETRIES} retries: {e}")
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
        return ""

    def estimate_tokens(self, text: str) -> int:
        return int(len(text) / 1.5)

    def get_usage(self) -> dict:
        return self._usage.copy()

    def reset_usage(self) -> None:
        self._usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
