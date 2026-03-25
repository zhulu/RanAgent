from __future__ import annotations

import json
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
    def _load_payload(tool_input: str) -> dict[str, str]:
        if not tool_input.strip():
            raise ValueError("tool_input 不能为空，且必须是 JSON 字符串")
        payload = json.loads(tool_input)
        if not isinstance(payload, dict):
            raise ValueError("tool_input 必须是 JSON 对象")
        return {str(key): str(value) for key, value in payload.items()}

    @staticmethod
    def _ok(message: str) -> ToolResult:
        return ToolResult(content=message)

    @staticmethod
    def _fail(exc: Exception) -> ToolResult:
        return ToolResult(content=f"文件工具执行失败：{exc}")


class ReadFileTool(WorkspacePathMixin):
    name = "read_file"
    description = '读取工作目录中的文本文件，入参示例 {"path":"doc/a.txt"}'

    def run(self, tool_input: str) -> ToolResult:
        try:
            payload = self._load_payload(tool_input)
            path = self._resolve_path(payload["path"], must_exist=True)
            if path.is_dir():
                raise IsADirectoryError(f"目标是目录而不是文件: {path}")
            return self._ok(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return self._fail(exc)


class WriteFileTool(WorkspacePathMixin):
    name = "write_file"
    description = '写入文本文件，入参示例 {"path":"notes/todo.txt","content":"hello"}'

    def run(self, tool_input: str) -> ToolResult:
        try:
            payload = self._load_payload(tool_input)
            path = self._resolve_path(payload["path"])
            content = payload.get("content", "")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return self._ok(f"已写入文件：{path}")
        except Exception as exc:
            return self._fail(exc)


class RenameFileTool(WorkspacePathMixin):
    name = "rename_file"
    description = '重命名文件但保持目录不变，入参示例 {"path":"a.txt","new_name":"b.txt"}'

    def run(self, tool_input: str) -> ToolResult:
        try:
            payload = self._load_payload(tool_input)
            source = self._resolve_path(payload["path"], must_exist=True)
            if source.is_dir():
                raise IsADirectoryError(f"目标是目录而不是文件: {source}")
            new_name = payload["new_name"]
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

    def run(self, tool_input: str) -> ToolResult:
        try:
            payload = self._load_payload(tool_input)
            source = self._resolve_path(payload["source"], must_exist=True)
            if source.is_dir():
                raise IsADirectoryError(f"目标是目录而不是文件: {source}")
            destination = self._resolve_path(payload["destination"])
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.rename(destination)
            return self._ok(f"已移动文件：{source} -> {destination}")
        except Exception as exc:
            return self._fail(exc)


class RemoveFileTool(WorkspacePathMixin):
    name = "rm_file"
    description = '删除文件，入参示例 {"path":"notes/old.txt"}'

    def run(self, tool_input: str) -> ToolResult:
        try:
            payload = self._load_payload(tool_input)
            path = self._resolve_path(payload["path"], must_exist=True)
            if path.is_dir():
                raise IsADirectoryError(f"目标是目录而不是文件: {path}")
            path.unlink()
            return self._ok(f"已删除文件：{path}")
        except Exception as exc:
            return self._fail(exc)
