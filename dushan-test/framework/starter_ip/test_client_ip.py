from ipaddress import IPv4Network

import pytest
from starlette.datastructures import Headers

from framework.starter_ip.core.client_ip_resolver import ClientIpResolver

pytestmark = pytest.mark.unit


def test_resolve_client_ip_ignores_forwarded_headers_without_trusted_proxy() -> None:
    headers = {
        "X-Forwarded-For": "8.8.8.8",
        "Forwarded": "for=1.1.1.1",
        "X-Real-IP": "8.8.4.4",
    }

    assert ClientIpResolver.resolve_client_ip(headers, "10.0.0.5", []) == "10.0.0.5"


def test_resolve_client_ip_selects_first_untrusted_xff_hop_from_right() -> None:
    headers = {"X-Forwarded-For": "1.1.1.1, 8.8.8.8, 10.0.0.9"}

    assert (
        ClientIpResolver.resolve_client_ip(headers, "10.0.0.5", [IPv4Network("10.0.0.0/8")])
        == "8.8.8.8"
    )


def test_resolve_client_ip_selects_first_untrusted_forwarded_hop_from_right() -> None:
    headers = {"Forwarded": "for=8.8.8.8, for=1.1.1.1, for=10.0.0.9"}

    assert (
        ClientIpResolver.resolve_client_ip(headers, "10.0.0.5", [IPv4Network("10.0.0.0/8")])
        == "1.1.1.1"
    )


def test_resolve_client_ip_accepts_forwarded_for_from_trusted_proxy() -> None:
    headers = {"Forwarded": 'proto=https; for="[2001:4860:4860::8888]"'}

    assert (
        ClientIpResolver.resolve_client_ip(headers, "10.0.0.5", [IPv4Network("10.0.0.0/8")])
        == "2001:4860:4860::8888"
    )


def test_resolve_client_ip_combines_repeated_forwarded_fields() -> None:
    headers = Headers(
        raw=[
            (b"forwarded", b"for=8.8.8.8"),
            (b"forwarded", b"for=10.0.0.9"),
        ]
    )

    assert (
        ClientIpResolver.resolve_client_ip(headers, "10.0.0.5", [IPv4Network("10.0.0.0/8")])
        == "8.8.8.8"
    )


def test_resolve_client_ip_allows_quoted_delimiters_in_forwarded_extensions() -> None:
    headers = {"Forwarded": 'for=8.8.8.8;host="edge,a;internal"'}

    assert (
        ClientIpResolver.resolve_client_ip(headers, "10.0.0.5", [IPv4Network("10.0.0.0/8")])
        == "8.8.8.8"
    )


@pytest.mark.parametrize(
    ("header_name", "header_value", "expected_ip"),
    [
        ("X-Forwarded-For", "1.1.1.1:43210", "1.1.1.1"),
        ("X-Forwarded-For", '"1.1.1.1"', "1.1.1.1"),
        ("X-Forwarded-For", "2001:4860:4860::8888", "2001:4860:4860::8888"),
        ("X-Forwarded-For", "[2001:4860:4860::8888]", "2001:4860:4860::8888"),
        ("X-Forwarded-For", '"[2001:4860:4860::8888]:443"', "2001:4860:4860::8888"),
        ("X-Real-IP", "2001:4860:4860::8888", "2001:4860:4860::8888"),
        ("Forwarded", 'for="1.1.1.1:43210"', "1.1.1.1"),
        ("Forwarded", 'for="[2001:4860:4860::8888]:443"', "2001:4860:4860::8888"),
    ],
)
def test_resolve_client_ip_parses_supported_forwarded_nodes(
    header_name: str,
    header_value: str,
    expected_ip: str,
) -> None:
    assert (
        ClientIpResolver.resolve_client_ip(
            {header_name: header_value}, "10.0.0.5", [IPv4Network("10.0.0.0/8")]
        )
        == expected_ip
    )


@pytest.mark.parametrize(
    ("header_name", "header_value"),
    [
        ("X-Forwarded-For", "8.8.8.8, unknown, 10.0.0.9"),
        ("X-Forwarded-For", '8.8.8.8, "1.1.1.1, 10.0.0.9'),
        ("Forwarded", "for=8.8.8.8, for=_hidden, for=10.0.0.9"),
        ("Forwarded", 'for=8.8.8.8, for="1.1.1.1, for=10.0.0.9'),
        ("Forwarded", 'for=8.8.8.8, for="1.1.1.1:not-a-port", for=10.0.0.9'),
        ("Forwarded", 'for=8.8.8.8, for="1.1.1.1:65536", for=10.0.0.9'),
        ("Forwarded", "for=8.8.8.8;for=1.1.1.1, for=10.0.0.9"),
    ],
)
def test_resolve_client_ip_rejects_malformed_active_chain(
    header_name: str, header_value: str
) -> None:
    assert (
        ClientIpResolver.resolve_client_ip(
            {header_name: header_value}, "10.0.0.5", [IPv4Network("10.0.0.0/8")]
        )
        == "10.0.0.5"
    )


def test_resolve_client_ip_falls_back_to_peer_when_forwarded_values_are_invalid() -> None:
    headers = {"X-Forwarded-For": "unknown, not-an-ip", "Forwarded": "for=_hidden"}

    assert (
        ClientIpResolver.resolve_client_ip(headers, "10.0.0.5", [IPv4Network("10.0.0.0/8")])
        == "10.0.0.5"
    )


def test_resolve_client_ip_honors_forwarded_header_priority() -> None:
    headers = {
        "X-Forwarded-For": "1.1.1.1",
        "Forwarded": "for=8.8.8.8",
        "X-Real-IP": "8.8.4.4",
    }

    assert (
        ClientIpResolver.resolve_client_ip(headers, "10.0.0.5", [IPv4Network("10.0.0.0/8")])
        == "1.1.1.1"
    )


def test_resolve_client_ip_does_not_use_lower_priority_header_after_invalid_forwarded() -> None:
    headers = {"Forwarded": "for=_hidden", "X-Real-IP": "8.8.4.4"}

    assert (
        ClientIpResolver.resolve_client_ip(headers, "10.0.0.5", [IPv4Network("10.0.0.0/8")])
        == "10.0.0.5"
    )


def test_resolve_client_ip_normalizes_ipv4_mapped_ipv6_node() -> None:
    headers = {"X-Forwarded-For": '"[::ffff:8.8.8.8]:443"'}

    assert (
        ClientIpResolver.resolve_client_ip(headers, "10.0.0.5", [IPv4Network("10.0.0.0/8")])
        == "8.8.8.8"
    )


def test_resolve_client_ip_selects_bare_ipv6_from_multi_hop_xff() -> None:
    headers = {"X-Forwarded-For": "2001:4860:4860::8888, 10.0.0.9"}

    assert (
        ClientIpResolver.resolve_client_ip(headers, "10.0.0.5", [IPv4Network("10.0.0.0/8")])
        == "2001:4860:4860::8888"
    )


def test_resolve_client_ip_normalizes_compressed_ipv6_peer() -> None:
    assert (
        ClientIpResolver.resolve_client_ip({}, "2001:4860:4860:0:0:0:0:8888", [])
        == "2001:4860:4860::8888"
    )


@pytest.mark.parametrize(
    ("raw_ip", "expected"),
    [
        ("8.8.8.8", True),
        ("2001:4860:4860::8888", True),
        ("::ffff:8.8.8.8", True),
        ("100.64.0.1", False),
        ("192.0.2.1", False),
        ("198.18.0.1", False),
        ("224.0.0.1", False),
        ("fd00::1", False),
        ("fe80::1", False),
        ("ff02::1", False),
        ("not-an-ip", False),
    ],
)
def test_is_public_ip_uses_global_address_classification(raw_ip: str, expected: bool) -> None:
    assert ClientIpResolver.is_public_ip(raw_ip) is expected


def test_request_scheme_uses_forwarded_proto_only_from_trusted_peer() -> None:
    assert (
        ClientIpResolver.resolve_request_scheme(
            {"X-Forwarded-Proto": "https"},
            "10.0.0.5",
            [IPv4Network("10.0.0.0/8")],
            "http",
        )
        == "https"
    )
    assert (
        ClientIpResolver.resolve_request_scheme(
            {"X-Forwarded-Proto": "https"},
            "203.0.113.5",
            [IPv4Network("10.0.0.0/8")],
            "http",
        )
        == "http"
    )


@pytest.mark.parametrize("forwarded_proto", ["ftp", "https,http", ""])
def test_request_scheme_rejects_invalid_forwarded_proto(forwarded_proto: str) -> None:
    assert (
        ClientIpResolver.resolve_request_scheme(
            {"X-Forwarded-Proto": forwarded_proto},
            "10.0.0.5",
            [IPv4Network("10.0.0.0/8")],
            "http",
        )
        == "http"
    )
