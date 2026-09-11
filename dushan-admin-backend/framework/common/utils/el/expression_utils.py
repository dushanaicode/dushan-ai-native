from collections.abc import Mapping

from jinja2 import StrictUndefined

from framework.common.utils.el.expression_environment import ExpressionEnvironment
from framework.common.utils.el.expression_options import ExpressionOptions
from framework.common.utils.el.expression_safety_policy import ExpressionSafetyPolicy
from framework.common.utils.el.native_expression_environment import NativeExpressionEnvironment


class ExpressionUtils:
    """显式启用的受限 Jinja 文本与表达式工具。

    例如 eval_expression("{{ count > 1 }}", {"count": 2}) 返回 True。
    输入只允许普通数据；缺变量、格式错误和越界均抛错，不记录模板或上下文。
    输出是普通文本，不是经过 HTML 安全处理的内容。
    """

    def __init__(self, options: ExpressionOptions):
        """以应用配置创建两个实例环境，不注册全局模板或上下文。"""
        self._options = options
        self._policy = ExpressionSafetyPolicy(options)
        self._text_env = ExpressionEnvironment(
            undefined=StrictUndefined, autoescape=False, cache_size=0
        )
        self._native_env = NativeExpressionEnvironment(
            undefined=StrictUndefined, autoescape=False, cache_size=0
        )
        self._text_env.globals.clear()
        self._native_env.globals.clear()

    def render_text(self, template_str: str, context: Mapping[str, object]) -> str:
        """渲染文本并检查输出容量，空模板返回空字符串。"""
        data = dict(context)
        self._policy.validate(template_str, self._text_env)
        self._policy.validate_data(data, max_bytes=self._options.max_context_bytes)
        result = self._text_env.from_string(template_str).render(data)
        if len(result.encode("utf-8")) > self._options.max_output_bytes:
            raise ValueError("表达式输出超过上限")
        return result

    def eval_expression(self, expression: str, context: Mapping[str, object]) -> object:
        """计算原生结果并检查容量和类型，不将缺失变量当作 None。"""
        data = dict(context)
        self._policy.validate(expression, self._native_env)
        self._policy.validate_data(data, max_bytes=self._options.max_context_bytes)
        result = self._native_env.from_string(expression).render(data)
        self._policy.validate_data(result, max_bytes=self._options.max_output_bytes)
        return result

    def batch_render(
        self,
        expressions: list[str],
        context: Mapping[str, object],
        extra_context: Mapping[str, object] | None = None,
    ) -> dict[str, str]:
        """批量渲染，显式附加上下文覆盖同名基础键。"""
        data = dict(context)
        if extra_context is not None:
            data.update(extra_context)
        return {expression: self.render_text(expression, data) for expression in expressions}

    def parse_expressions(
        self, context: Mapping[str, object], expressions: list[str]
    ) -> dict[str, object]:
        """批量计算表达式，任一失败即交给调用方处理。"""
        return {expression: self.eval_expression(expression, context) for expression in expressions}
