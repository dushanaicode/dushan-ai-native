from datetime import UTC, datetime, timedelta

import pytest
from config_factory import ConfigFactory

from framework.common.datetime.core.date_range_builder import DateRangeBuilder
from framework.common.datetime.core.date_utils import DateUtils
from framework.common.datetime.core.datetime_options import DateTimeOptions
from framework.common.enums.date_interval_enum import DateIntervalEnum
from framework.starter_config.provider.bootstrap_config_error import BootstrapConfigError
from framework.starter_config.provider.bootstrap_config_provider import BootstrapConfigProvider
from server.config.application_settings import ApplicationSettings
from server.starter_server import create_app

pytestmark = pytest.mark.unit


def dates(**overrides):
    return DateUtils(ConfigFactory.build(DateTimeOptions, "datetime", **overrides))


def test_naive_time_has_one_consistent_timezone_interpretation():
    helper = dates(timezone="Asia/Shanghai")
    local = datetime(2024, 2, 29, 12)
    expected = datetime(2024, 2, 29, 4, tzinfo=UTC)
    assert helper.to_utc(local) == expected
    assert helper.to_timestamp_seconds(local) == int(expected.timestamp())
    assert helper.to_timestamp_millis(local) == int(expected.timestamp() * 1000)
    assert helper.from_timestamp_millis(helper.to_timestamp_millis(local)) == helper.localize(local)
    assert helper.parse_isoformat("2024-02-29T04:00:00+00:00").hour == 12
    assert helper.format_datetime(local) == "2024-02-29 12:00:00"
    assert "+08:00" in helper.format_datetime_iso(local)
    with pytest.raises(ValueError):
        helper.parse_isoformat("invalid")


def test_timezone_instances_are_independent_and_preserve_fractional_offsets():
    assert dates(timezone="Asia/Kathmandu").get_timezone_offset() == 5.75
    assert dates(timezone="UTC").get_timezone_offset() == 0
    assert dates(timezone="Asia/Shanghai").get_timezone_offset() == 8
    zone = dates(timezone="America/New_York").get_timezone()
    start = datetime(2024, 11, 3, 1, 30, tzinfo=zone, fold=0)
    end = datetime(2024, 11, 3, 1, 10, tzinfo=zone, fold=1)
    ranges = DateRangeBuilder.build(start, end, DateIntervalEnum.DAY, max_segments=1)
    assert ranges == [[start, end]]
    assert (
        dates(timezone="America/New_York").format_date_range(start, end, DateIntervalEnum.DAY)
        == "2024-11-03"
    )
    with pytest.raises(ValueError):
        DateRangeBuilder.build(end, start, DateIntervalEnum.DAY, max_segments=1)


def test_timestamp_precision_and_maximum_calendar_boundary():
    helper = dates(timezone="UTC")
    before_epoch = datetime(1969, 12, 31, 23, 59, 59, 999500, tzinfo=UTC)
    assert helper.to_timestamp_millis(before_epoch) == -1
    assert helper.to_timestamp_seconds(before_epoch) == -1
    for milliseconds in (-1, 0, 1712345678123):
        assert (
            helper.to_timestamp_millis(helper.from_timestamp_millis(milliseconds)) == milliseconds
        )
    start = datetime(9999, 12, 1, tzinfo=UTC)
    end = datetime.max.replace(tzinfo=UTC)
    for interval in DateIntervalEnum:
        ranges = DateRangeBuilder.build(start, end, interval, max_segments=40)
        assert ranges[-1][1] == end


@pytest.mark.parametrize("value", [datetime(2024, 3, 10, 2, 30), datetime(2024, 11, 3, 1, 30)])
def test_dst_naive_gaps_and_ambiguity_require_explicit_offset(value):
    with pytest.raises(ValueError, match="DST"):
        dates(timezone="America/New_York").localize(value)


@pytest.mark.parametrize("interval", list(DateIntervalEnum))
def test_calendar_ranges_cover_closed_interval_without_overlap(interval):
    helper = dates(timezone="UTC")
    start = datetime(2023, 12, 29, tzinfo=UTC)
    end = datetime(2024, 4, 2, 13, tzinfo=UTC)
    ranges = DateRangeBuilder.build(start, end, interval, max_segments=1000)
    assert ranges[0][0] == start
    assert ranges[-1][1] == end
    for previous, current in zip(ranges, ranges[1:]):
        assert previous[1] + timedelta(microseconds=1) == current[0]
    assert helper.format_date_range(start, end, interval)


def test_month_end_and_equal_boundary_do_not_skip_or_overrun():
    helper = dates(timezone="UTC")
    moment = datetime(2024, 2, 15, 12, 35, tzinfo=UTC)
    assert helper.end_of_month(moment) == datetime(2024, 2, 29, 23, 59, 59, 999999, tzinfo=UTC)
    assert DateRangeBuilder.build(moment, moment, DateIntervalEnum.MONTH, max_segments=1) == [
        [moment, moment]
    ]
    with pytest.raises(ValueError, match="上限"):
        dates(max_range_segments=1).get_date_range_list(
            datetime(2024, 1, 1), datetime(2024, 1, 3), DateIntervalEnum.DAY
        )
    with pytest.raises(ValueError):
        DateRangeBuilder.build(
            moment, moment - timedelta(days=1), DateIntervalEnum.DAY, max_segments=1
        )


def test_new_config_sections_have_sources_and_reach_component_instances(config_dir):
    root = config_dir()
    app = create_app(
        base_dir=root, environ={"DATETIME_TIMEZONE": "UTC", "EXPRESSION_ENABLED": "true"}
    )
    ctx = app.state.bootstrap
    assert ctx.date_utils.get_timezone_name() == "UTC"
    assert ctx.expression_utils.eval_expression("{{ count + 1 }}", {"count": 2}) == 3
    assert ctx.config_sources["datetime.timezone"] == "环境变量 DATETIME_TIMEZONE"
    assert ctx.config_sources["expression.enabled"] == "环境变量 EXPRESSION_ENABLED"


@pytest.mark.parametrize(
    "environ,field",
    [
        ({"DATETIME_TIMEZONE": "No/SuchZone"}, "datetime.timezone"),
        ({"DATETIME_FORMAT": "%Q"}, "datetime.format"),
        ({"EXPRESSION_MAX_DEPTH": "0"}, "expression.max_depth"),
    ],
)
def test_invalid_config_points_to_source(config_dir, environ, field):
    with pytest.raises(BootstrapConfigError) as caught:
        BootstrapConfigProvider.load(config_dir(), environ=environ).get_config(ApplicationSettings)
    assert field in str(caught.value)
