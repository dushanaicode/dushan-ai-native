from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from types import SimpleNamespace
from typing import Annotated
from unittest.mock import Mock
from uuid import UUID

import pytest
from pydantic import create_model

from fixtures.config_factory import ConfigFactory
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_security.bizlog.biz_log_service import BizLogService
from framework.starter_security.bizlog.diff_field import DiffField
from framework.starter_security.bizlog.diff_renderer import DiffRenderer
from framework.starter_security.bizlog.log_record_context import LogRecordContext
from framework.starter_security.config.security_settings import SecuritySettings


@pytest.fixture
def settings():
    """使用产品配置创建不依赖数据库的日志设置。"""
    return SecuritySettings.model_validate(ConfigFactory.values()["config"]["models"]["security"])


def value_model(annotation=object, *, field="value", label="值", formatter=None):
    """为单个差异字段构造模型，避免借用业务 VO。"""
    return create_model(
        "DiffValue",
        **{field: (Annotated[annotation, DiffField(label, formatter=formatter)], ...)},
    )


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        (Decimal("1.00"), Decimal("2.00"), "值: 1.00 → 2.00"),
        (Decimal("1.0"), Decimal("1.00"), ""),
        (
            Decimal("0.12345678901234567890"),
            Decimal("0.12345678901234567891"),
            "值: 0.12345678901234567890 → 0.12345678901234567891",
        ),
        (date(2026, 1, 1), date(2026, 1, 2), "值: 2026-01-01 → 2026-01-02"),
        (
            datetime(2026, 1, 1),
            datetime(2026, 1, 2),
            "值: 2026-01-01T00:00:00 → 2026-01-02T00:00:00",
        ),
        (time(1), time(2), "值: 01:00:00 → 02:00:00"),
        (timedelta(days=1), timedelta(days=2), "值: P1D → P2D"),
        (
            UUID(int=1),
            UUID(int=2),
            "值: 00000000-0000-0000-0000-000000000001 → 00000000-0000-0000-0000-000000000002",
        ),
    ],
)
async def test_scalar_comparison_precedes_serialization(settings, old, new, expected):
    """真实值决定变化，合法模型标量展示时保留精度和类型含义。"""
    model = value_model()
    assert await DiffRenderer(settings).render(model(value=old), model(value=new)) == expected


async def test_enum_uses_declared_value(settings):
    """枚举展示其声明值，不退化成类型名称。"""
    state = Enum("LogState", {"DRAFT": "draft", "READY": "ready"})
    model = value_model(state)
    assert (
        await DiffRenderer(settings).render(model(value=state.DRAFT), model(value=state.READY))
        == "值: draft → ready"
    )


@pytest.mark.parametrize("field", ["id_card", "identityNumber", "password"])
@pytest.mark.parametrize("formatter", [None, "_MASK"])
async def test_sensitive_change_survives_identical_display(settings, field, formatter):
    """敏感字段即使净化或掩码后相同，也必须留下变化记录。"""
    model = value_model(str, field=field, label="身份证", formatter=formatter)
    before = model(**{field: "110101199001011234"})
    after = model(**{field: "110101199002011234"})
    content = await DiffRenderer(settings).render(before, after)
    assert "身份证" in content and "已变更" in content
    assert before.model_dump()[field] not in content
    assert after.model_dump()[field] not in content
    assert await DiffRenderer(settings).render(before, before) == ""


async def test_mask_receives_original_sensitive_value(settings):
    """内置掩码接收身份证原值，安全展示保留首尾字符。"""
    model = value_model(str, field="id_card", label="证件", formatter="_MASK")
    content = await DiffRenderer(settings).render(
        model(id_card="110101199001011234"), model(id_card="220202199002022235")
    )
    assert content == "证件: 1****************4 → 2****************5"


async def test_masked_collection_reports_same_display_change(settings):
    """集合内的敏感原值变化即使掩码相同，也保留变更标记。"""
    model = value_model(list[str], field="id_card", label="证件", formatter="_MASK")
    assert (
        await DiffRenderer(settings).render(
            model(id_card=["110101199001011234"]), model(id_card=["110101199002011234"])
        )
        == "证件已变更"
    )


@pytest.mark.parametrize("asynchronous", [False, True])
async def test_formatter_receives_original_decimal(settings, asynchronous):
    """同步和异步转换器都取得原始 Decimal，不接收净化占位符。"""
    calls = []

    def format_amount(value):
        """校验类型并生成金额展示。"""
        assert isinstance(value, Decimal)
        calls.append(value)
        return f"{value:.2f}元"

    async def format_amount_async(value):
        """按异步调用约定格式化金额。"""
        return format_amount(value)

    model = value_model(Decimal, formatter="amount")
    formatter = format_amount_async if asynchronous else format_amount
    renderer = DiffRenderer(settings, (("amount", formatter),))
    assert await renderer.render(model(value="1"), model(value="2")) == "值: 1.00元 → 2.00元"
    assert calls == [Decimal("1"), Decimal("2")]
    calls.clear()
    assert await renderer.render(model(value="1.0"), model(value="1.00")) == ""
    assert calls == []


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        (["a", "b", "a"], ["b", "b", "c"], "值: 添加 b (x1), c (x1)；删除 a (x2)"),
        (["a", "b", "a"], ["a", "a", "b"], ""),
        (None, [], ""),
        (None, ["a"], "值: 添加 a (x1)；删除 "),
        (["a"], None, "值: 添加 ；删除 a (x1)"),
        (
            [Decimal("1.0"), Decimal("1.00")],
            [Decimal("1.000"), Decimal("2.00")],
            "值: 添加 2.00 (x1)；删除 1.00 (x1)",
        ),
        (
            [{"amount": Decimal("1.00")}],
            [{"amount": Decimal("2.00")}],
            "值: 添加 {'amount': '2.00'} (x1)；删除 {'amount': '1.00'} (x1)",
        ),
        ([{"id_card": "private-old"}], [{"id_card": "private-new"}], "值已变更"),
    ],
)
async def test_collection_comparison_preserves_values_and_multiplicity(
    settings, old, new, expected
):
    """集合按真实元素计算增删，忽略顺序并保留重复次数和空集合语义。"""
    model = value_model(list[object] | None)
    assert await DiffRenderer(settings).render(model(value=old), model(value=new)) == expected


async def test_collection_formatter_receives_decimal(settings):
    """集合元素转换器仍接收真实类型，不经过 JSON 往返。"""
    model = value_model(list[Decimal], formatter="amount")
    calls = []

    def format_amount(value):
        """记录转换器输入并返回数值。"""
        assert isinstance(value, Decimal)
        calls.append(value)
        return value

    content = await DiffRenderer(settings, (("amount", format_amount),)).render(
        model(value=[Decimal("1")]), model(value=[Decimal("2")])
    )
    assert content == "值: 添加 2 (x1)；删除 1 (x1)"
    assert calls == [Decimal("2"), Decimal("1")]


async def test_projection_and_unknown_objects_do_not_expose_private_values(settings):
    """忽略与未声明字段不参与比较，未知对象不会调用字符串转换。"""
    model = create_model(
        "ProjectedValue",
        value=(Annotated[object, DiffField("值")], ...),
        ignored=(Annotated[str, DiffField("忽略", ignore=True)], ...),
        unmarked=(str, ...),
    )
    old, new = Mock(), Mock()
    for value in (old, new):
        value.__str__ = Mock(side_effect=AssertionError("不得转换未知对象"))
        value.__repr__ = Mock(side_effect=AssertionError("不得展示未知对象"))
    before = model(value=old, ignored="private-old", unmarked="unmarked-old")
    after = model(value=new, ignored="private-new", unmarked="unmarked-new")
    assert await DiffRenderer(settings).render(before, after) == "值已变更"
    assert (
        await DiffRenderer(settings).render(before, after.model_copy(update={"value": old})) == ""
    )
    for value in (old, new):
        value.__str__.assert_not_called()
        value.__repr__.assert_not_called()


async def test_formatter_output_is_sanitized(settings):
    """批准的格式器输出仍经过凭证文本净化。"""
    model = value_model(str, formatter="label")
    renderer = DiffRenderer(settings, (("label", lambda value: f"token={value}"),))
    content = await renderer.render(model(value="private-old"), model(value="private-new"))
    assert "已变更" in content
    assert "private" not in content


async def test_record_diff_only_puts_safe_text_in_context(settings, monkeypatch):
    """业务入口将真实变化的安全文本写入上下文，不保存敏感原值。"""
    application = Mock()
    binding = SimpleNamespace(application=application)
    monkeypatch.setattr(ApplicationContext, "current_execution", lambda: binding)
    context = LogRecordContext(application)
    service = BizLogService(settings, None, None, context, None)
    model = value_model(str, field="id_card", label="身份证")
    with context.scope():
        await service.record_diff(model(id_card="private-old"), model(id_card="private-new"))
        assert context.values() == {"diff": "身份证已变更"}
    assert service.failed == 0


async def test_bounds_and_invalid_formatter_registration(settings):
    """保留长度上限、字段条数上限及格式器注册约束。"""
    model = create_model(
        "BoundedValue",
        first=(Annotated[str, DiffField("一")], ...),
        second=(Annotated[str, DiffField("二")], ...),
    )
    renderer = DiffRenderer(
        settings.model_copy(update={"bizlog_max_length": 128, "bizlog_max_diff_items": 1})
    )
    before = model(first="old", second="old")
    after = model(first="new", second="new")
    assert await renderer.render(before, after) == "一: old → new[差异已截断]"
    content = await renderer.render(before, after.model_copy(update={"first": "x" * 4096}))
    assert len(content) == 128 and content.endswith("[差异已截断]")
    with pytest.raises(ValueError, match="差异转换函数名称为空或重复"):
        DiffRenderer(settings, (("_MASK", str),))
