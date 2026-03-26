from __future__ import annotations

import ast
import operator

from agent_app.tools.base import ToolResult


class CalculatorTool:
    name = "calculator"
    description = "执行基础四则运算，例如 2 * (3 + 4)"
    input_schema = {"expression": "string, arithmetic expression using numbers and + - * / ()"}
    example_input = "2 * (3 + 4)"

    _operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.USub: operator.neg,
    }

    def run(self, tool_input: str) -> ToolResult:
        expression = tool_input.strip()
        if not expression:
            return ToolResult(content="未提供算式。")

        try:
            value = self._eval(ast.parse(expression, mode="eval").body)
        except Exception as exc:
            return ToolResult(content=f"计算失败：{exc}")
        return ToolResult(content=f"{expression} = {value}")

    def _eval(self, node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in self._operators:
            left = self._eval(node.left)
            right = self._eval(node.right)
            return self._operators[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in self._operators:
            operand = self._eval(node.operand)
            return self._operators[type(node.op)](operand)
        raise ValueError("仅支持数字和 + - * / ()")
