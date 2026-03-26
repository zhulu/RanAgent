from __future__ import annotations

from datetime import datetime

from agent_app.tools.base import ToolResult


class TimeNowTool:
    name = "time_now"
    description = "返回当前本地时间"
    input_schema = {}
    example_input = ""

    def run(self, tool_input: str) -> ToolResult:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return ToolResult(content=f"当前本地时间：{now}")
