from jinja2.nativetypes import NativeEnvironment

from framework.starter_security.bizlog.expression.expression_environment import (
    ExpressionEnvironment,
)


class NativeExpressionEnvironment(ExpressionEnvironment, NativeEnvironment):
    """在相同访问限制下返回表达式的原生值。"""
