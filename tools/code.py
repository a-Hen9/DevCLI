"""Code manipulation tools using tree-sitter for AST parsing."""
import asyncio
import re
from pathlib import Path

from devcli.tools.base import Tool, ToolContext, ToolResult


class CodeTool(Tool):
    name = "code"

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        action = params.get("action")
        if action == "parse_ast":
            return await self.parse_ast(params.get("file_path", ""), context)
        if action == "insert_method":
            return await self.insert_method(
                params.get("file_path", ""),
                params.get("method_code", ""),
                params.get("class_name", ""),
                context,
            )
        if action == "find_references":
            return await self.find_references(
                params.get("symbol", ""), context
            )
        if action == "apply_patch":
            return await self.apply_patch(
                params.get("file_path", ""),
                params.get("original", ""),
                params.get("replacement", ""),
                context,
            )
        return ToolResult(success=False, error=f"Unknown action: {action}")

    async def parse_ast(self, file_path: str, context: ToolContext) -> ToolResult:
        try:
            import tree_sitter_python as tspython
            from tree_sitter import Language, Parser

            PY_LANGUAGE = Language(tspython.language())
            parser = Parser(PY_LANGUAGE)

            target = Path(context.work_dir) / file_path
            code = target.read_text(encoding="utf-8")
            tree = parser.parse(bytes(code, "utf-8"))

            root = tree.root_node
            symbols = self._extract_symbols(root, code)
            return ToolResult(success=True, output="\n".join(symbols))
        except ImportError:
            return await self._parse_ast_regex(file_path, context)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _extract_symbols(self, node, code: str) -> list[str]:
        symbols = []
        if node.type == "function_definition":
            name = self._get_node_text(node.children[1], code)
            symbols.append(f"function: {name}")
        elif node.type == "class_definition":
            name = self._get_node_text(node.children[1], code)
            symbols.append(f"class: {name}")
        for child in node.children:
            symbols.extend(self._extract_symbols(child, code))
        return symbols

    def _get_node_text(self, node, code: str) -> str:
        start = node.start_point
        end = node.end_point
        lines = code.split("\n")
        if start[0] == end[0]:
            return lines[start[0]][start[1]:end[1]]
        result = [lines[start[0]][start[1]:]]
        for i in range(start[0] + 1, end[0]):
            result.append(lines[i])
        result.append(lines[end[0]][:end[1]])
        return "\n".join(result)

    async def _parse_ast_regex(self, file_path: str, context: ToolContext) -> ToolResult:
        try:
            target = Path(context.work_dir) / file_path
            code = target.read_text(encoding="utf-8")
            classes = re.findall(r"^class\s+(\w+)", code, re.MULTILINE)
            functions = re.findall(r"^(?:async\s+)?def\s+(\w+)", code, re.MULTILINE)
            symbols = [f"class: {c}" for c in classes] + [f"function: {f}" for f in functions]
            return ToolResult(success=True, output="\n".join(symbols))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def insert_method(
        self, file_path: str, method_code: str, class_name: str, context: ToolContext
    ) -> ToolResult:
        try:
            target = Path(context.work_dir) / file_path
            code = target.read_text(encoding="utf-8")
            pattern = rf"(class {class_name}.*?:\n)"
            match = re.search(pattern, code, re.DOTALL)
            if not match:
                return ToolResult(success=False, error=f"Class {class_name} not found")
            indent = "    "
            indented_method = "\n".join(indent + line for line in method_code.split("\n"))
            new_code = code[:match.end()] + "\n" + indented_method + "\n" + code[match.end():]
            target.write_text(new_code, encoding="utf-8")
            return ToolResult(success=True, output=f"Inserted method into {class_name}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def find_references(self, symbol: str, context: ToolContext) -> ToolResult:
        try:
            results = []
            work_dir = Path(context.work_dir)
            for ext in ["*.py", "*.ts", "*.tsx", "*.js", "*.jsx"]:
                for file in work_dir.rglob(ext):
                    content = file.read_text(encoding="utf-8", errors="ignore")
                    lines = content.split("\n")
                    for i, line in enumerate(lines, 1):
                        if symbol in line:
                            results.append(f"{file.relative_to(work_dir)}:{i}: {line.strip()}")
            return ToolResult(success=True, output="\n".join(results[:50]))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def apply_patch(
        self, file_path: str, original: str, replacement: str, context: ToolContext
    ) -> ToolResult:
        try:
            target = Path(context.work_dir) / file_path
            code = target.read_text(encoding="utf-8")
            if original not in code:
                return ToolResult(success=False, error="Original text not found in file")
            new_code = code.replace(original, replacement, 1)
            target.write_text(new_code, encoding="utf-8")
            return ToolResult(success=True, output=f"Patched {file_path}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
