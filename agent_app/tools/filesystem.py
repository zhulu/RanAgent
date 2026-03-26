from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from agent_app.tools.base import ToolResult


class WorkspacePathMixin:
    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root.resolve()

    def _resolve_path(self, raw_path: str, *, must_exist: bool = False) -> Path:
        if not raw_path:
            raise ValueError("path 不能为空")

        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = self._workspace_root / candidate

        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(self._workspace_root)
        except ValueError as exc:
            raise ValueError("只允许访问工作目录内的文件") from exc

        if must_exist and not resolved.exists():
            raise FileNotFoundError(f"文件不存在: {resolved}")
        return resolved

    @staticmethod
    def _load_payload(tool_input: str) -> dict[str, object]:
        if not tool_input.strip():
            raise ValueError("tool_input 不能为空，且必须是 JSON 字符串")
        payload = json.loads(tool_input)
        if not isinstance(payload, dict):
            raise ValueError("tool_input 必须是 JSON 对象")
        return payload

    @staticmethod
    def _as_bool(value: object, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y", "on"}
        return bool(value)

    @staticmethod
    def _as_int(value: object, default: int) -> int:
        if value is None:
            return default
        return int(value)

    def _relative_display(self, path: Path) -> str:
        return str(path.relative_to(self._workspace_root)).replace("\\", "/")

    @staticmethod
    def _ok(message: str) -> ToolResult:
        return ToolResult(content=message)

    @staticmethod
    def _fail(exc: Exception) -> ToolResult:
        return ToolResult(content=f"文件工具执行失败：{exc}")


class ReadFileTool(WorkspacePathMixin):
    name = "read_file"
    description = '读取工作目录中的文本文件，入参示例 {"path":"doc/a.txt"}'
    input_schema = {"path": "string, relative or absolute path under workspace"}
    example_input = '{"path":"doc/a.txt"}'

    def run(self, tool_input: str) -> ToolResult:
        try:
            payload = self._load_payload(tool_input)
            path = self._resolve_path(str(payload["path"]), must_exist=True)
            if path.is_dir():
                raise IsADirectoryError(f"目标是目录而不是文件: {path}")
            return self._ok(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return self._fail(exc)


class WriteFileTool(WorkspacePathMixin):
    name = "write_file"
    description = '写入文本文件，入参示例 {"path":"notes/todo.txt","content":"hello"}'
    input_schema = {
        "path": "string, target file path under workspace",
        "content": "string, utf-8 text to write",
    }
    example_input = '{"path":"notes/todo.txt","content":"hello"}'

    def run(self, tool_input: str) -> ToolResult:
        try:
            payload = self._load_payload(tool_input)
            path = self._resolve_path(str(payload["path"]))
            content = str(payload.get("content", ""))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return self._ok(f"已写入文件：{path}")
        except Exception as exc:
            return self._fail(exc)


class RenameFileTool(WorkspacePathMixin):
    name = "rename_file"
    description = '重命名文件但保持目录不变，入参示例 {"path":"a.txt","new_name":"b.txt"}'
    input_schema = {
        "path": "string, existing file path under workspace",
        "new_name": "string, new file name only, no path separators",
    }
    example_input = '{"path":"a.txt","new_name":"b.txt"}'

    def run(self, tool_input: str) -> ToolResult:
        try:
            payload = self._load_payload(tool_input)
            source = self._resolve_path(str(payload["path"]), must_exist=True)
            if source.is_dir():
                raise IsADirectoryError(f"目标是目录而不是文件: {source}")
            new_name = str(payload["new_name"])
            if Path(new_name).name != new_name:
                raise ValueError("new_name 只能是文件名，不能包含路径")
            target = source.with_name(new_name)
            source.rename(target)
            return self._ok(f"已重命名文件：{source} -> {target}")
        except Exception as exc:
            return self._fail(exc)


class MoveFileTool(WorkspacePathMixin):
    name = "move_file"
    description = '移动文件到新位置，入参示例 {"source":"a.txt","destination":"archive/a.txt"}'
    input_schema = {
        "source": "string, existing file path under workspace",
        "destination": "string, destination path under workspace",
    }
    example_input = '{"source":"a.txt","destination":"archive/a.txt"}'

    def run(self, tool_input: str) -> ToolResult:
        try:
            payload = self._load_payload(tool_input)
            source = self._resolve_path(str(payload["source"]), must_exist=True)
            if source.is_dir():
                raise IsADirectoryError(f"目标是目录而不是文件: {source}")
            destination = self._resolve_path(str(payload["destination"]))
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.rename(destination)
            return self._ok(f"已移动文件：{source} -> {destination}")
        except Exception as exc:
            return self._fail(exc)


class RemoveFileTool(WorkspacePathMixin):
    name = "rm_file"
    description = '删除文件，入参示例 {"path":"notes/old.txt"}'
    input_schema = {"path": "string, existing file path under workspace"}
    example_input = '{"path":"notes/old.txt"}'

    def run(self, tool_input: str) -> ToolResult:
        try:
            payload = self._load_payload(tool_input)
            path = self._resolve_path(str(payload["path"]), must_exist=True)
            if path.is_dir():
                raise IsADirectoryError(f"目标是目录而不是文件: {path}")
            path.unlink()
            return self._ok(f"已删除文件：{path}")
        except Exception as exc:
            return self._fail(exc)


class ListDirTool(WorkspacePathMixin):
    name = "list_dir"
    description = (
        '列出目录内容，入参示例 {"path":".","recursive":false,"max_entries":50}'
    )
    input_schema = {
        "path": "string, directory path under workspace",
        "recursive": "boolean, whether to recurse into subdirectories",
        "max_entries": "integer, maximum returned entries",
    }
    example_input = '{"path":".","recursive":false,"max_entries":50}'

    def run(self, tool_input: str) -> ToolResult:
        try:
            payload = self._load_payload(tool_input)
            path = self._resolve_path(str(payload.get("path", ".")), must_exist=True)
            recursive = self._as_bool(payload.get("recursive"), default=False)
            max_entries = self._as_int(payload.get("max_entries"), default=50)
            if not path.is_dir():
                raise NotADirectoryError(f"目标不是目录: {path}")

            iterator = path.rglob("*") if recursive else path.iterdir()
            entries = sorted(iterator, key=lambda item: self._relative_display(item))
            lines: list[str] = []
            for entry in entries[:max_entries]:
                prefix = "[dir]" if entry.is_dir() else "[file]"
                lines.append(f"{prefix} {self._relative_display(entry)}")

            if not lines:
                return self._ok("目录为空。")
            return self._ok("\n".join(lines))
        except Exception as exc:
            return self._fail(exc)


class StatFileTool(WorkspacePathMixin):
    name = "stat_file"
    description = '查看文件或目录状态，入参示例 {"path":"README.md"}'
    input_schema = {"path": "string, file or directory path under workspace"}
    example_input = '{"path":"README.md"}'

    def run(self, tool_input: str) -> ToolResult:
        try:
            payload = self._load_payload(tool_input)
            path = self._resolve_path(str(payload["path"]), must_exist=True)
            stat = path.stat()
            result = {
                "path": self._relative_display(path),
                "exists": True,
                "is_dir": path.is_dir(),
                "size": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            }
            return self._ok(json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as exc:
            return self._fail(exc)


class SearchInFilesTool(WorkspacePathMixin):
    name = "search_in_files"
    description = (
        '在工作目录中搜索文本，入参示例 '
        '{"pattern":"TODO","path":".","glob":"*.py","max_matches":20}'
    )
    input_schema = {
        "pattern": "string, text to search for",
        "path": "string, root path under workspace",
        "glob": "string, file glob filter such as *.py",
        "max_matches": "integer, maximum returned matches",
        "case_sensitive": "boolean, whether match should be case sensitive",
    }
    example_input = '{"pattern":"TODO","path":".","glob":"*.py","max_matches":20}'

    def run(self, tool_input: str) -> ToolResult:
        try:
            payload = self._load_payload(tool_input)
            pattern = str(payload["pattern"])
            search_root = self._resolve_path(str(payload.get("path", ".")), must_exist=True)
            glob_pattern = str(payload.get("glob", "*"))
            max_matches = self._as_int(payload.get("max_matches"), default=20)
            case_sensitive = self._as_bool(payload.get("case_sensitive"), default=False)
            if not pattern:
                raise ValueError("pattern 不能为空")

            matched_lines: list[str] = []
            for file_path in self._iter_candidate_files(search_root, glob_pattern):
                if len(matched_lines) >= max_matches:
                    break
                try:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if "\x00" in text:
                    continue

                for line_number, line in enumerate(text.splitlines(), start=1):
                    if self._matches(line, pattern, case_sensitive):
                        matched_lines.append(
                            f"{self._relative_display(file_path)}:{line_number}: {line.strip()}"
                        )
                        if len(matched_lines) >= max_matches:
                            break

            if not matched_lines:
                return self._ok("未找到匹配内容。")
            return self._ok("\n".join(matched_lines))
        except Exception as exc:
            return self._fail(exc)

    def _iter_candidate_files(self, search_root: Path, glob_pattern: str) -> list[Path]:
        if search_root.is_file():
            return [search_root]

        return [
            path
            for path in sorted(search_root.rglob(glob_pattern))
            if path.is_file()
        ]

    @staticmethod
    def _matches(line: str, pattern: str, case_sensitive: bool) -> bool:
        if case_sensitive:
            return pattern in line
        return pattern.lower() in line.lower()
