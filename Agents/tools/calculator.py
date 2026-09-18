"""
Safe Calculator Tool for Agent Math Evaluation.
"""

import ast
import math
import operator
from langchain_core.tools import tool

# Supported operators for safe math evaluation
_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_expr(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    elif isinstance(node, ast.BinOp):
        left = _eval_expr(node.left)
        right = _eval_expr(node.right)
        op_type = type(node.op)
        if op_type in _OPERATORS:
            return _OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        operand = _eval_expr(node.operand)
        op_type = type(node.op)
        if op_type in _OPERATORS:
            return _OPERATORS[op_type](operand)
    raise ValueError(f"Unsupported math expression or operation")


@tool
def calculator_tool(expression: str) -> str:
    """Evaluates mathematical expressions safely (e.g. '25 * 4 + (100 / 5)')."""
    try:
        parsed = ast.parse(expression, mode="eval")
        result = _eval_expr(parsed.body)
        return str(result)
    except Exception as exc:
        return f"Error evaluating expression '{expression}': {str(exc)}"
