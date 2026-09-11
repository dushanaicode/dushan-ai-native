import math

from jinja2 import Environment, Undefined, nodes

from framework.common.utils.el.expression_options import ExpressionOptions
from framework.common.utils.json.json_utils import JsonUtils


class ExpressionSafetyPolicy:
    """限制 Jinja 表达式与数据输入；这不是运行任意代码的进程沙箱。"""

    _allowed_nodes = (
        nodes.Template,
        nodes.Output,
        nodes.TemplateData,
        nodes.Const,
        nodes.Name,
        nodes.Getitem,
        nodes.Getattr,
        nodes.List,
        nodes.Tuple,
        nodes.Dict,
        nodes.Pair,
        nodes.Compare,
        nodes.Operand,
        nodes.And,
        nodes.Or,
        nodes.Not,
        nodes.Add,
        nodes.Sub,
        nodes.Div,
        nodes.FloorDiv,
        nodes.Neg,
        nodes.Pos,
        nodes.CondExpr,
    )

    def __init__(self, options: ExpressionOptions):
        """使用应用明确提供的安全容量限制。"""
        self.options = options

    def validate(self, expression: str, environment: Environment) -> None:
        """检查完整语法树；禁止语句、调用、过滤器、测试、乘幂和乘法扩张。"""
        if not self.options.enabled:
            raise RuntimeError("表达式能力未启用")
        if len(expression) > self.options.max_length:
            raise ValueError("表达式长度超过上限")
        root = environment.parse(expression)
        pending = [(root, 0)]
        while pending:
            node, depth = pending.pop()
            if depth > self.options.max_depth or type(node) not in self._allowed_nodes:
                raise ValueError("表达式包含不允许的语法或嵌套过深")
            if (
                isinstance(node, nodes.Getattr)
                and node.attr.startswith("_")
                or isinstance(node, nodes.Name)
                and node.name.startswith("_")
            ):
                raise ValueError("表达式不能访问内部名称")
            pending.extend((child, depth + 1) for child in node.iter_child_nodes())

    def validate_data(self, value: object, *, max_bytes: int) -> None:
        """只接受有限的 JSON 数据，不允许对象方法、循环引用和超深容器。"""
        pending = [(value, 0)]
        remaining = max_bytes
        while pending:
            item, depth = pending.pop()
            remaining -= len(item.encode("utf-8")) if type(item) is str else 1
            if remaining < 0:
                raise ValueError("表达式数据大小超过上限")
            if depth > self.options.max_depth:
                raise ValueError("表达式数据嵌套超过上限")
            if isinstance(item, Undefined):
                str(item)
            if type(item) is dict:
                if any(type(key) is not str for key in item):
                    raise ValueError("表达式对象的键必须是字符串")
                remaining -= sum(len(key.encode("utf-8")) for key in item)
                if len(item) > remaining:
                    raise ValueError("表达式数据大小超过上限")
                pending.extend((child, depth + 1) for child in item.values())
            elif type(item) in (list, tuple):
                if len(item) > remaining:
                    raise ValueError("表达式数据大小超过上限")
                pending.extend((child, depth + 1) for child in item)
            elif type(item) not in (str, int, float, bool, type(None)):
                raise ValueError("表达式只能接收和返回 JSON 数据")
            elif (
                type(item) is int
                and item.bit_length() > 63
                or type(item) is float
                and not math.isfinite(item)
            ):
                raise ValueError("表达式数值超出有限范围")
        if len(JsonUtils.to_json_bytes(value)) > max_bytes:
            raise ValueError("表达式数据大小超过上限")
