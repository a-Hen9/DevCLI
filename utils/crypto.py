"""Encryption utilities for secure API key storage using Fernet symmetric encryption."""
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


class CryptoError(Exception):
    pass


class KeyManager:
    def __init__(self, key_path: Path | None = None):
        self._key_path = key_path or (Path.home() / ".devcli" / ".key")

    def _ensure_key(self) -> bytes:
        if self._key_path.exists():
            return self._key_path.read_bytes()
        key = Fernet.generate_key()
        self._key_path.parent.mkdir(parents=True, exist_ok=True)
        self._key_path.write_bytes(key)
        os.chmod(self._key_path, 0o600)
        return key

    def encrypt(self, plaintext: str) -> str:
        key = self._ensure_key()
        f = Fernet(key)
        return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        try:
            key = self._ensure_key()
            f = Fernet(key)
            return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            raise CryptoError("Decryption failed: invalid key or corrupted data.")
