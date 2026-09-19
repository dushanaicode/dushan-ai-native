import asyncio
from types import SimpleNamespace
from typing import Annotated

import httpx
import pytest
from fastapi import Depends, Request
from pydantic import BaseModel

from fixtures.public_web_app import create_public_app
from framework.starter_di.decorators.di_dependency import DiDependency
from framework.starter_excel.converter.area_converter import AreaConverter
from framework.starter_excel.model.excel_column import ExcelColumn
from framework.starter_excel.model.excel_providers import ExcelProviders
from framework.starter_excel.reader.excel_reader import ExcelReader
from framework.starter_excel.writer.excel_writer import ExcelWriter
from framework.starter_ip.client.ip_location_http_client import IpLocationHttpClient
from framework.starter_ip.config.ip_settings import IpSettings
from framework.starter_ip.core.client_ip_resolver import ClientIpResolver
from framework.starter_ip.core.ip2region_database import Ip2RegionDatabase
from framework.starter_ip.definitions.constants.ip_error_codes import IpErrorCodes
from framework.starter_ip.exception.ip_exception import IpException
from framework.starter_ip.model.area import Area
from framework.starter_ip.service.area_service import AreaService
from framework.starter_ip.service.ip_location_service import IpLocationService
from server.bootstrap.bootstrapper import BootstrapError

pytestmark = pytest.mark.unit


class AreaRow(BaseModel):
    area: Annotated[Area, ExcelColumn("地区", converter=AreaConverter())]
    count: Annotated[int, ExcelColumn("数量")]


class PlainRow(BaseModel):
    count: Annotated[int, ExcelColumn("数量")]


def upload(stream):
    return SimpleNamespace(
        file=stream,
        filename="地区.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


async def test_real_area_xlsx_and_local_ipv4_ipv6_use_application_di(config_dir, monkeypatch):
    """真实模块声明和应用资源步骤共同支撑 Excel 地区读写，无缓存或网络服务。"""
    monkeypatch.setattr(
        IpLocationHttpClient, "open", lambda self: pytest.fail("离线应用不能创建在线客户端")
    )
    app = create_public_app(
        base_dir=config_dir({"scanner": {"enabled": False}}),
        environ={"IP_ENABLED": "true", "CACHE_ENABLED": "false", "DATABASE_ENABLED": "false"},
    )
    async with app.router.lifespan_context(app):
        runtime = app.state.application_context
        with runtime.execution():
            areas = runtime.container.get(AreaService)
            locations = runtime.container.get(IpLocationService)
            writer = runtime.container.get(ExcelWriter)
            reader = runtime.container.get(ExcelReader)
            providers = ExcelProviders(areas=areas)
            area = areas.get_area(110101)
            assert areas.format_area_path(area.id) == "中国/北京市/北京市/东城区"
            with await writer.write(
                "地区", AreaRow, [AreaRow(area=area, count=7)], providers=providers
            ) as stream:
                result = await reader.read(upload(stream), AreaRow, providers=providers)
                assert not stream.closed
            assert result[0].area is area and result[0].count == 7
            ipv4, ipv6 = await asyncio.gather(
                locations.lookup("8.8.8.8"), locations.lookup("2001:4860:4860::8888")
            )
            assert ipv4.status == ipv6.status == "found"
            assert ipv4.provider == ipv6.provider == "ip2region"
            assert ipv4.location and ipv6.location
    assert app.state.ip is None
    with pytest.raises(IpException):
        areas.get_area(110101)
    with pytest.raises(IpException):
        await locations.lookup("8.8.8.8")


async def test_plain_xlsx_runs_with_ip_cache_and_database_disabled(config_dir, monkeypatch):
    """禁用外部资源时，已装配的 XLSX 核心仍可用。"""
    for owner in (AreaService, Ip2RegionDatabase):
        monkeypatch.setattr(owner, "initialize", lambda *args: pytest.fail("禁用资源被加载"))
    app = create_public_app(base_dir=config_dir(), environ={})
    async with app.router.lifespan_context(app):
        runtime = app.state.application_context
        with runtime.execution():
            writer = runtime.container.get(ExcelWriter)
            reader = runtime.container.get(ExcelReader)
            with await writer.write("数量", PlainRow, [PlainRow(count=0)]) as stream:
                assert await reader.read(upload(stream), PlainRow) == [PlainRow(count=0)]


async def test_area_resources_are_isolated_and_one_app_can_close_first(config_dir):
    root = config_dir()
    environ = {"IP_ENABLED": "true", "IP_LOCAL_ENABLED": "false"}
    first, second = (
        create_public_app(base_dir=root, environ=environ),
        create_public_app(base_dir=root, environ=environ),
    )
    async with second.router.lifespan_context(second):
        async with first.router.lifespan_context(first):
            first_areas, second_areas = first.state.ip.areas, second.state.ip.areas
            first_node, second_node = first_areas.get_area(110101), second_areas.get_area(110101)
            assert first_areas is not second_areas and first_node is not second_node
            assert first_areas.format_area_path(110101) == second_areas.format_area_path(110101)
        with pytest.raises(IpException):
            first_areas.get_area(110101)
        assert second_areas.get_area(110101) is second_node
    with pytest.raises(IpException):
        second_areas.get_area(110101)


async def test_failed_ip_startup_releases_already_loaded_areas(config_dir, tmp_path, monkeypatch):
    captured = []
    initialize = AreaService.initialize

    def record_initialize(self, *args):
        initialize(self, *args)
        captured.append(self)

    monkeypatch.setattr(AreaService, "initialize", record_initialize)
    app = create_public_app(
        base_dir=config_dir(),
        environ={"IP_ENABLED": "true", "IP_LOCAL_DATA_DIR": str(tmp_path / "missing-xdb")},
    )
    with pytest.raises(BootstrapError) as caught:
        async with app.router.lifespan_context(app):
            pytest.fail("缺失 XDB 的应用不能就绪")
    assert isinstance(caught.value.__cause__, IpException)
    assert not app.state.bootstrap.ready and app.state.ip is None
    assert len(captured) == 1
    with pytest.raises(IpException):
        captured[0].get_area(110101)


async def test_http_client_ip_uses_real_peer_and_application_proxy_config(config_dir):
    app = create_public_app(
        base_dir=config_dir(), environ={"IP_TRUSTED_PROXY_CIDRS": '["10.0.0.0/8"]'}
    )

    @app.get("/client-ip")
    async def client_ip(request: Request, settings: IpSettings = Depends(DiDependency(IpSettings))):
        return {
            "ip": ClientIpResolver.resolve_client_ip(
                request.headers, request.client.host, settings.trusted_proxy_cidrs
            )
        }

    async with app.router.lifespan_context(app):
        for peer, forwarded, expected in (
            ("192.0.2.1", "8.8.8.8", "192.0.2.1"),
            ("10.0.0.2", "1.1.1.1, 198.51.100.10, 10.0.0.1", "198.51.100.10"),
        ):
            transport = httpx.ASGITransport(app=app, client=(peer, 32100))
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/client-ip", headers={"X-Forwarded-For": forwarded})
                assert response.status_code == 200 and response.json() == {"ip": expected}


async def test_host_cancellation_closes_ip_resources(config_dir):
    app = create_public_app(
        base_dir=config_dir(), environ={"IP_ENABLED": "true", "IP_LOCAL_ENABLED": "false"}
    )
    ready = asyncio.Event()

    async def host():
        async with app.router.lifespan_context(app):
            ready.set()
            await asyncio.Event().wait()

    task = asyncio.create_task(host())
    await asyncio.wait_for(ready.wait(), 10)
    areas = app.state.ip.areas
    task.cancel("host-stop")
    with pytest.raises(asyncio.CancelledError, match="host-stop"):
        await task
    assert not app.state.bootstrap.ready and app.state.ip is None
    with pytest.raises(IpException):
        areas.get_area(110101)


async def test_explicit_ip_enable_requires_di(config_dir):
    app = create_public_app(
        base_dir=config_dir(), environ={"IP_ENABLED": "true", "DI_ENABLED": "false"}
    )
    with pytest.raises(BootstrapError) as caught:
        async with app.router.lifespan_context(app):
            pytest.fail("没有 DI 的 IP 资源不能就绪")
    assert isinstance(caught.value.__cause__, ValueError)
    assert "DI" in str(caught.value.__cause__)
    assert not app.state.bootstrap.ready


@pytest.mark.parametrize(
    "family,selected,other",
    [
        ("ipv4", "8.8.8.8", "2001:4860:4860::8888"),
        ("ipv6", "2001:4860:4860::8888", "8.8.8.8"),
    ],
)
async def test_application_loads_only_the_requested_ip_family(config_dir, family, selected, other):
    """环境覆盖通过真实 DI/启动步骤生效，未加载族与正常未知结果明确区分。"""
    app = create_public_app(
        base_dir=config_dir(),
        environ={"IP_ENABLED": "true", "IP_LOCAL_FAMILIES": f'["{family}"]'},
    )
    async with app.router.lifespan_context(app):
        starter = app.state.ip
        configured = app.state.bootstrap.definitions.configuration.get_config(IpSettings)
        assert configured.local_families == (family,)
        found = await starter.location.lookup(selected)
        unavailable = await starter.location.lookup(other)
        assert found.status == "found" and found.provider == "ip2region"
        assert unavailable.status == "unavailable" and unavailable.location is None
        assert any("not_enabled" in reason for reason in unavailable.failures)
        with pytest.raises(IpException) as not_enabled:
            starter.database.search(other)
        assert not_enabled.value.error_code is IpErrorCodes.FAMILY_NOT_ENABLED
    with pytest.raises(IpException) as closed:
        starter.database.search(selected)
    assert closed.value.error_code is IpErrorCodes.NOT_INITIALIZED
