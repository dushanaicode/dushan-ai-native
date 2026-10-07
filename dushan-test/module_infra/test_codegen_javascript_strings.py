import ast

import pytest

from module_infra.util.codegen.codegen_engine_utils import CodegenEngineUtils


@pytest.mark.parametrize(
    "value",
    [
        "日期与时间",
        "营业日 🗓",
        '客户 "姓名"',
        "O'Brien",
        '客户 "O\'Brien"',
        "</script><script>alert('x')</script>&",
        "反斜杠\\和单引号'与双引号\"",
        r"原样保留 \u00ef 和 \u003c",
        "控制字符\x00\x1b\n\r\t",
    ],
)
def test_javascript_metadata_round_trips_without_script_boundaries(value):
    engine = CodegenEngineUtils()
    literal = engine._get_env().from_string("{{ value | jsrepr }}").render(value=value)
    assert ast.literal_eval(literal) == value
    assert "<" not in literal
    assert ">" not in literal
    assert "&" not in literal


def test_jinja_json_keeps_unicode_and_javascript_uses_frontend_quote_style():
    engine = CodegenEngineUtils()
    assert engine._get_env().from_string("{{ value | tojson }}").render(value="日期") == '"日期"'
    assert engine.javascript_string("日期") == "'日期'"
    assert engine.javascript_string("\x1b</script>") == r"'\u001B\u003C/script\u003E'"
