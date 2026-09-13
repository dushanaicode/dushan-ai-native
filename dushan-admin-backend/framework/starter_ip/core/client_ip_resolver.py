import ipaddress
from collections.abc import Mapping, Sequence
from typing import Final

HEADER_FORWARDED: Final = "forwarded"
HEADER_X_FORWARDED_FOR: Final = "x-forwarded-for"
HEADER_X_REAL_IP: Final = "x-real-ip"
FORWARDED_FOR_PARAM: Final = "for"
SCHEME_HTTP: Final = "http"
SCHEME_HTTPS: Final = "https"
MAX_NETWORK_PORT: Final = 65535
MAX_PORT_DIGITS: Final = 5
UNKNOWN_IP_MARKERS: Final[frozenset[str]] = frozenset({"", "unknown"})
TRUSTED_FORWARDING_HEADERS: Final = frozenset(
    {HEADER_FORWARDED, HEADER_X_FORWARDED_FOR, HEADER_X_REAL_IP}
)
TRUSTED_SCHEMES: Final = frozenset({SCHEME_HTTP, SCHEME_HTTPS})


class ClientIpResolver:
    """唯一请求 IP 规则；只有 socket peer 属于显式可信网段时才读取转发信息。"""

    @staticmethod
    def resolve_client_ip(
        headers: Mapping[str, str],
        peer_host: str | None,
        trusted_proxy_cidrs: Sequence[ipaddress.IPv4Network | ipaddress.IPv6Network],
    ) -> str | None:
        """按 socket peer 和可信代理链确定规范化的客户端地址。"""
        peer_ip = ClientIpResolver.normalize_ip(peer_host)
        if peer_ip is None:
            return None
        if not ClientIpResolver._is_trusted_proxy(peer_ip, trusted_proxy_cidrs):
            return peer_ip
        forwarding_headers = ClientIpResolver._collect_forwarding_headers(headers)
        if sum(len(value) for values in forwarding_headers.values() for value in values) > 16384:
            return peer_ip
        if HEADER_X_FORWARDED_FOR in forwarding_headers:
            chain = ClientIpResolver._parse_x_forwarded_for(
                ",".join(forwarding_headers[HEADER_X_FORWARDED_FOR])
            )
        elif HEADER_FORWARDED in forwarding_headers:
            chain = ClientIpResolver._parse_forwarded(
                ",".join(forwarding_headers[HEADER_FORWARDED])
            )
        elif HEADER_X_REAL_IP in forwarding_headers:
            real_ip_values = forwarding_headers[HEADER_X_REAL_IP]
            if len(real_ip_values) != 1:
                return peer_ip
            real_ip = ClientIpResolver._parse_forwarded_node(real_ip_values[0])
            return real_ip if real_ip is not None else peer_ip
        else:
            return peer_ip
        if chain is None:
            return peer_ip
        return ClientIpResolver._resolve_proxy_chain(chain, peer_ip, trusted_proxy_cidrs)

    @staticmethod
    def resolve_request_scheme(
        headers: Mapping[str, str],
        peer_host: str | None,
        trusted_proxy_cidrs: Sequence[ipaddress.IPv4Network | ipaddress.IPv6Network],
        current_scheme: str,
    ) -> str:
        """仅采纳可信直接代理提供的单值 X-Forwarded-Proto。"""
        peer_ip = ClientIpResolver.normalize_ip(peer_host)
        if peer_ip is None or not ClientIpResolver._is_trusted_proxy(peer_ip, trusted_proxy_cidrs):
            return current_scheme
        forwarded_proto_values = [
            value for key, value in headers.items() if key.lower() == "x-forwarded-proto"
        ]
        if len(forwarded_proto_values) != 1:
            return current_scheme
        forwarded_scheme = forwarded_proto_values[0].strip().lower()
        return forwarded_scheme if forwarded_scheme in TRUSTED_SCHEMES else current_scheme

    @staticmethod
    def normalize_ip(raw_ip: str | None) -> str | None:
        """标准化双栈地址；IPv4-mapped IPv6 统一为 IPv4，不接受 zone id。"""
        if raw_ip is None:
            return None
        value = raw_ip.strip()
        if value.lower() in UNKNOWN_IP_MARKERS or "%" in value:
            return None
        try:
            parsed_ip = ipaddress.ip_address(value)
        except ValueError:
            return None
        if isinstance(parsed_ip, ipaddress.IPv6Address) and parsed_ip.ipv4_mapped is not None:
            return str(parsed_ip.ipv4_mapped)
        return parsed_ip.compressed

    @staticmethod
    def is_public_ip(raw_ip: str) -> bool:
        """仅公网单播地址允许交给在线归属地服务。"""
        parsed_ip = ClientIpResolver._parse_ip(raw_ip)
        if parsed_ip is None:
            return False
        return parsed_ip.is_global and (not parsed_ip.is_multicast)

    @staticmethod
    def _parse_x_forwarded_for(raw_header: str) -> list[str] | None:
        chain: list[str] = []
        raw_nodes = ClientIpResolver._split_quoted_header(raw_header, ",")
        if raw_nodes is None:
            return None
        for raw_node in raw_nodes:
            node = ClientIpResolver._parse_forwarded_node(raw_node)
            if node is None:
                return None
            chain.append(node)
        return chain

    @staticmethod
    def _parse_forwarded(raw_header: str) -> list[str] | None:
        chain: list[str] = []
        elements = ClientIpResolver._split_quoted_header(raw_header, ",")
        if elements is None:
            return None
        for element in elements:
            raw_node: str | None = None
            raw_params = ClientIpResolver._split_quoted_header(element, ";")
            if raw_params is None:
                return None
            for raw_param in raw_params:
                name, separator, value = raw_param.strip().partition("=")
                if not separator:
                    return None
                if name.strip().lower() != FORWARDED_FOR_PARAM:
                    continue
                if raw_node is not None:
                    return None
                raw_node = value.strip()
            if raw_node is None:
                return None
            node = ClientIpResolver._parse_forwarded_node(raw_node)
            if node is None:
                return None
            chain.append(node)
        return chain

    @staticmethod
    def _split_quoted_header(raw_header: str, delimiter: str) -> list[str] | None:
        parts: list[str] = []
        current: list[str] = []
        quoted = False
        escaped = False
        for character in raw_header:
            if escaped:
                current.append(character)
                escaped = False
                continue
            if quoted and character == "\\":
                current.append(character)
                escaped = True
                continue
            if character == '"':
                current.append(character)
                quoted = not quoted
                continue
            if character == delimiter and (not quoted):
                parts.append("".join(current).strip())
                current.clear()
                continue
            current.append(character)
        if quoted or escaped:
            return None
        parts.append("".join(current).strip())
        return parts

    @staticmethod
    def _collect_forwarding_headers(headers: Mapping[str, str]) -> dict[str, list[str]]:
        collected: dict[str, list[str]] = {}
        for raw_name, value in headers.items():
            name = raw_name.lower()
            if name not in TRUSTED_FORWARDING_HEADERS:
                continue
            if name not in collected:
                collected[name] = []
            collected[name].append(value)
        return collected

    @staticmethod
    def _parse_forwarded_node(raw_node: str) -> str | None:
        node = raw_node.strip()
        if node.startswith('"') != node.endswith('"'):
            return None
        if node.startswith('"'):
            node = node[1:-1]
        if not node:
            return None
        if node != node.strip():
            return None
        if '"' in node or "\\" in node:
            return None
        normalized_node = ClientIpResolver.normalize_ip(node)
        if normalized_node is not None:
            return normalized_node
        raw_address = ClientIpResolver._extract_node_address(node)
        if raw_address is None:
            return None
        return ClientIpResolver.normalize_ip(raw_address)

    @staticmethod
    def _extract_node_address(node: str) -> str | None:
        if node.startswith("["):
            closing_bracket = node.find("]")
            if closing_bracket < 2:
                return None
            raw_address = node[1:closing_bracket]
            suffix = node[closing_bracket + 1 :]
            if ":" not in raw_address:
                return None
            if suffix and (
                not suffix.startswith(":") or not ClientIpResolver._is_valid_port(suffix[1:])
            ):
                return None
        else:
            raw_address, separator, raw_port = node.partition(":")
            if separator and (not ClientIpResolver._is_valid_port(raw_port)):
                return None
        return raw_address

    @staticmethod
    def _is_valid_port(raw_port: str) -> bool:
        return (
            raw_port.isascii()
            and raw_port.isdecimal()
            and (len(raw_port) <= MAX_PORT_DIGITS)
            and (int(raw_port) <= MAX_NETWORK_PORT)
        )

    @staticmethod
    def _resolve_proxy_chain(
        chain: Sequence[str],
        peer_ip: str,
        trusted_proxy_cidrs: Sequence[ipaddress.IPv4Network | ipaddress.IPv6Network],
    ) -> str:
        for candidate in reversed((*chain, peer_ip)):
            if not ClientIpResolver._is_trusted_proxy(candidate, trusted_proxy_cidrs):
                return candidate
        return peer_ip

    @staticmethod
    def _is_trusted_proxy(
        normalized_ip: str,
        trusted_proxy_cidrs: Sequence[ipaddress.IPv4Network | ipaddress.IPv6Network],
    ) -> bool:
        parsed_ip = ipaddress.ip_address(normalized_ip)
        return any(parsed_ip in network for network in trusted_proxy_cidrs)

    @staticmethod
    def _parse_ip(raw_ip: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
        normalized = ClientIpResolver.normalize_ip(raw_ip)
        if normalized is None:
            return None
        return ipaddress.ip_address(normalized)
