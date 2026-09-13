import pytest
from jinja2 import UndefinedError
from jinja2.exceptions import SecurityError

from fixtures.config_factory import ConfigFactory
from framework.common.utils.el.expression_options import ExpressionOptions
from framework.common.utils.el.expression_utils import ExpressionUtils

pytestmark = pytest.mark.unit


def expression(**overrides):
    return ExpressionUtils(
        ConfigFactory.build(ExpressionOptions, "expression", enabled=True, **overrides)
    )


def test_expressions_render_text_and_native_results():
    helper = expression()
    assert helper.render_text("你好 {{ user.name }}", {"user": {"name": "渡山"}}) == "你好 渡山"
    assert helper.eval_expression("{{ count > 1 }}", {"count": 2}) is True
    assert helper.eval_expression("{{ count + 1 }}", {"count": 2}) == 3
    assert helper.render_text("", {}) == ""
    assert helper.batch_render(["{{ name }}"], {"name": "base"}, {"name": "override"}) == {
        "{{ name }}": "override"
    }
    assert helper.parse_expressions({"n": 2}, ["{{ n - 1 }}"]) == {"{{ n - 1 }}": 1}


def test_disabled_expression_does_not_execute():
    helper = ExpressionUtils(ConfigFactory.build(ExpressionOptions, "expression"))
    with pytest.raises(RuntimeError, match="未启用"):
        helper.eval_expression("{{ 1 + 1 }}", {})


@pytest.mark.parametrize(
    "template",
    [
        "{{ ''.__class__.__mro__ }}",
        "{% for x in xs %}{{ x }}{% endfor %}",
        "{{ f() }}",
        "{{ value|attr('__class__') }}",
        "{{ 2 ** 10000 }}",
        "{{ 'x' * 10000 }}",
        "{{ value.items }}",
        "{{ value is defined }}",
    ],
)
def test_expression_rejects_code_access_or_expanding_syntax(template):
    with pytest.raises((ValueError, UndefinedError, SecurityError)):
        expression().eval_expression(template, {"value": {}, "xs": [1], "f": 1})


def test_missing_names_propagate_in_both_modes():
    with pytest.raises(UndefinedError):
        expression().render_text("{{ missing }}", {})
    with pytest.raises(UndefinedError):
        expression().eval_expression("{{ missing }}", {})


def test_expression_limits_apply_to_input_depth_and_output():
    with pytest.raises(ValueError):
        expression(max_length=2).render_text("long", {})
    with pytest.raises(ValueError):
        expression(max_context_bytes=4).render_text("{{ a }}", {"a": "payload"})
    with pytest.raises(ValueError):
        expression(max_output_bytes=4).render_text("{{ a }}{{ a }}", {"a": "long"})
    with pytest.raises(ValueError):
        expression(max_depth=2).eval_expression("{{ a }}", {"a": [[[1]]]})
    with pytest.raises(ValueError):
        expression().eval_expression("{{ a }}", {"a": object()})
    cyclic = []
    cyclic.append(cyclic)
    with pytest.raises(ValueError):
        expression().eval_expression("{{ a }}", {"a": cyclic})


def test_independent_options_do_not_share_enabled_state():
    disabled = ExpressionUtils(ConfigFactory.build(ExpressionOptions, "expression"))
    assert expression().eval_expression("{{ 1 }}", {}) == 1
    with pytest.raises(RuntimeError):
        disabled.render_text("anything", {})
