import os
import subprocess
import sys
from ipaddress import IPv4Network
from pathlib import Path

import pytest
from pydantic import ValidationError

from framework.starter_ip.config.ip_settings import IpSettings
from framework.starter_ip.core.client_ip_resolver import ClientIpResolver


@pytest.mark.parametrize(
    "key,value",
    [
        ("online_timeout_seconds", True),
        ("query_budget_seconds", float("inf")),
        ("query_budget_seconds", 0),
        ("cache_max_size", -1),
        ("online_max_response_bytes", 0),
        ("trusted_proxy_cidrs", ["not-a-cidr"]),
        ("area_csv_path", "relative.csv"),
        ("local_data_dir", ""),
        ("pconline_api_url", "http://example.com/api"),
        ("vore_api_url", "https://secret:password@example.com/api"),
        ("online_providers", ["vore", "vore"]),
    ],
)
def test_settings_enforce_explicit_resource_and_network_boundaries(ip_settings, key, value):
    with pytest.raises(ValidationError):
        ip_settings(**{key: value})


def test_configuration_has_no_code_defaults(ip_settings):
    assert all(field.is_required() for field in IpSettings.model_fields.values())
    settings = ip_settings(cache_max_size=0, unknown_cache_ttl_seconds=0)
    assert settings.cache_max_size == 0


def test_scoped_addresses_and_oversized_headers_are_rejected():
    assert ClientIpResolver.normalize_ip("fe80::1%eth0") is None
    assert (
        ClientIpResolver.resolve_client_ip(
            {"X-Forwarded-For": "8.8.8.8," * 3000}, "10.0.0.1", [IPv4Network("10.0.0.0/8")]
        )
        == "10.0.0.1"
    )
    assert (
        ClientIpResolver.resolve_client_ip(
            {"Forwarded": "for=8.8.8.8"}, None, [IPv4Network("0.0.0.0/0")]
        )
        is None
    )


def test_imports_do_not_open_resources_or_connect_network():
    package = Path(__file__).resolve().parents[3] / "dushan-admin-backend/framework/starter_ip"
    modules = [
        "framework.starter_ip." + ".".join(path.relative_to(package).with_suffix("").parts)
        for path in package.rglob("*.py")
        if path.name != "__init__.py"
    ]
    program = """
import importlib, sys
def audit(event, args):
    if event == 'socket.connect':
        raise AssertionError('import attempted network access')
    if event == 'open' and isinstance(args[0], str) and args[0].endswith(('.xdb', 'area.csv', 'manifest.json', 'area-manifest.json')):
        raise AssertionError('import opened a large/data resource')
sys.addaudithook(audit)
for name in sys.argv[1:]:
    importlib.import_module(name)
print(len(sys.argv)-1)
"""
    process = subprocess.run(
        [sys.executable, "-B", "-c", program, *modules],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert process.returncode == 0, process.stderr
    assert int(process.stdout) == len(modules) >= 15
