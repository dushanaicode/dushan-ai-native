import ipaddress
from pathlib import Path

import pytest
from pydantic import ValidationError

from framework.starter_ip.config.ip_settings import IpSettings
from framework.starter_ip.core.client_ip_resolver import ClientIpResolver
from framework.starter_ip.core.ip2region_database import Ip2RegionDatabase
from framework.starter_ip.exception.ip_exception import IpException
from framework.starter_ip.provider.ip2region_ip_location_provider import Ip2RegionIpLocationProvider
from framework.starter_ip.service.ip_location_service import IpLocationService
from framework.starter_ip.spi.ip_location_provider import IpLocationProvider


@pytest.mark.parametrize(
    "families,loaded", [(("ipv4",), {4}), (("ipv6",), {6}), (("ipv4", "ipv6"), {4, 6})]
)
def test_only_selected_family_is_read_and_validated(families, loaded, monkeypatch):
    original = Path.read_bytes
    reads = []

    def read(path):
        reads.append(path.name)
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read)
    database = Ip2RegionDatabase()
    database.initialize(families)
    try:
        assert set(database._searchers) == loaded
        assert "manifest.json" in reads and "LICENSE.md" in reads
        assert ("ip2region_v4.xdb" in reads) == (4 in loaded)
        assert ("ip2region_v6.xdb" in reads) == (6 in loaded)
        for family, ip in ((4, "1.2.3.4"), (6, "2604:a840:3::a04d")):
            if family in loaded:
                assert database.search(ip)
            else:
                with pytest.raises(IpException) as failure:
                    database.search(ip)
                assert failure.value.context["family"] == family
    finally:
        database.close()
    assert database._searchers is None


def test_single_family_still_rejects_corrupt_selected_resource(monkeypatch):
    original = Path.read_bytes

    def corrupt(path):
        data = original(path)
        return data[:-1] + bytes([data[-1] ^ 1]) if path.name == "ip2region_v4.xdb" else data

    monkeypatch.setattr(Path, "read_bytes", corrupt)
    database = Ip2RegionDatabase()
    with pytest.raises(IpException) as failure:
        database.initialize(("ipv4",))
    assert "SHA-256 mismatch" in str(failure.value.__cause__)
    assert database._searchers is None


async def test_disabled_family_is_unavailable_and_online_may_still_resolve(ip_settings):
    class Online(IpLocationProvider):
        name, online = "sample", True

        async def query(self, ip, remaining_seconds):
            return "在线地区"

    database = Ip2RegionDatabase()
    database.initialize(("ipv4",))
    local = Ip2RegionIpLocationProvider(database)
    offline = IpLocationService(
        ip_settings(local_families=["ipv4"], online_failure_policy="raise"), [local]
    )
    offline.open()
    online = IpLocationService(
        ip_settings(
            local_families=["ipv4"],
            online_enabled=True,
            online_providers=["sample"],
            online_failure_policy="raise",
        ),
        [local, Online()],
    )
    online.open()
    try:
        result = await offline.lookup("2604:a840:3::a04d")
        assert result.status == "unavailable"
        assert result.failures == ("ip2region:ipv6_not_enabled",)
        assert not offline._cache
        resolved = await online.lookup("2604:a840:3::a04d")
        assert resolved.status == "found" and resolved.provider == "sample"
        assert resolved.failures == ("ip2region:ipv6_not_enabled",)
    finally:
        await offline.close()
        await online.close()
        database.close()


@pytest.mark.parametrize("value", [[], ["ipv4", "ipv4"], ["IPV4"], ["ipv3"]])
def test_local_family_configuration_is_explicit(ip_settings, value):
    with pytest.raises(ValidationError):
        ip_settings(local_families=value)


def test_networks_are_parsed_at_configuration_boundary_only(ip_settings, monkeypatch):
    calls = []
    original = ipaddress.IPv4Network.__init__

    def record(network, address, strict=True):
        calls.append(address)
        original(network, address, strict)

    monkeypatch.setattr(ipaddress.IPv4Network, "__init__", record)
    settings = ip_settings(
        trusted_proxy_cidrs=[
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
            "127.0.0.0/8",
            "198.18.0.0/15",
        ]
    )
    startup_count = len(calls)
    assert startup_count == 5
    chain = ", ".join(["8.8.8.8"] + [f"10.0.0.{value}" for value in range(2, 12)])
    for _ in range(100):
        assert (
            ClientIpResolver.resolve_client_ip(
                {"X-Forwarded-For": chain}, "10.0.0.1", settings.trusted_proxy_cidrs
            )
            == "8.8.8.8"
        )
        assert (
            ClientIpResolver.resolve_request_scheme(
                {"X-Forwarded-Proto": "https"}, "10.0.0.1", settings.trusted_proxy_cidrs, "http"
            )
            == "https"
        )
    assert len(calls) == startup_count


def test_network_configuration_json_and_frozen_contract(ip_settings):
    settings = ip_settings(trusted_proxy_cidrs=["10.0.0.0/8", "2001:db8::/32"])
    assert isinstance(settings.trusted_proxy_cidrs[0], ipaddress.IPv4Network)
    assert isinstance(settings.trusted_proxy_cidrs[1], ipaddress.IPv6Network)
    assert settings.model_dump(mode="json")["trusted_proxy_cidrs"] == [
        "10.0.0.0/8",
        "2001:db8::/32",
    ]
    assert (
        IpSettings.model_validate_json(settings.model_dump_json()).trusted_proxy_cidrs
        == settings.trusted_proxy_cidrs
    )
    with pytest.raises(ValidationError):
        settings.trusted_proxy_cidrs = ()
    assert (
        ClientIpResolver.resolve_client_ip(
            {"X-Forwarded-For": "8.8.8.8"}, "invalid", settings.trusted_proxy_cidrs
        )
        is None
    )
    assert ClientIpResolver.resolve_client_ip({}, None, settings.trusted_proxy_cidrs) is None


@pytest.mark.parametrize("value", [[True], [2130706433], [["127.0.0.1", 32]], "10.0.0.0/8", {}])
def test_proxy_configuration_does_not_accept_numeric_network_shortcuts(ip_settings, value):
    with pytest.raises(ValidationError):
        ip_settings(trusted_proxy_cidrs=value)
