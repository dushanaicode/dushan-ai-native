from jinja2.sandbox import SandboxedEnvironment


class ExpressionEnvironment(SandboxedEnvironment):
    """禁止属性和函数调用，仅允许从已校验的数据容器读取值。"""

    def is_safe_attribute(self, obj: object, attr: str, value: object) -> bool:
        """对象真实属性一律不可见，字典键仍按 Jinja 语义访问。"""
        return False

    def is_safe_callable(self, obj: object) -> bool:
        """不开放来自上下文或环境的函数调用。"""
        return False
