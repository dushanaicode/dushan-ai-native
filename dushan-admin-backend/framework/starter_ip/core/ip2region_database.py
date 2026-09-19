import hashlib
import ipaddress
import json
import struct
from importlib.metadata import version
from pathlib import Path
from threading import RLock
from typing import Literal

import ip2region.searcher as xdb
import ip2region.util as xdb_util

from framework.starter_di.decorators.components import framework
from framework.starter_di.definitions.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_ip.core.client_ip_resolver import ClientIpResolver
from framework.starter_ip.definitions.constants.ip_error_codes import IpErrorCodes
from framework.starter_ip.exception.ip_exception import IpException


@framework(scope=ComponentScopeEnum.SINGLETON)
class Ip2RegionDatabase:
    """按配置加载应用独占的全内存 XDB；短同步查询与关闭共用锁。"""

    MANIFEST_SHA256 = "b87c5773b6e2d555639a83a5141bb80c7eabf1df7b6c12c947846a3b0eb5dfa8"

    def __init__(self) -> None:
        self._searchers: dict[int, xdb.Searcher] | None = None
        self._lock = RLock()

    def initialize(
        self, families: tuple[Literal["ipv4", "ipv6"], ...], data_dir: Path | None = None
    ) -> None:
        with self._lock:
            if self._searchers is not None:
                raise RuntimeError("XDB 已经初始化")
            path = (
                Path(__file__).resolve().parents[1] / "resources" / "ip2region" / "v3.17.0"
                if data_dir is None
                else data_dir
            )
            searchers = {}
            content = b""
            try:
                manifest_bytes = (path / "manifest.json").read_bytes()
                if hashlib.sha256(manifest_bytes).hexdigest() != self.MANIFEST_SHA256:
                    raise ValueError("ip2region manifest SHA-256 mismatch")
                manifest = json.loads(manifest_bytes)
                if version("py-ip2region") != manifest["package"]["version"]:
                    raise ValueError("py-ip2region binding version mismatch")
                self._read_artifact(path, manifest["license"])
                for family_name in families:
                    artifact = manifest[family_name]
                    family = artifact["ip_version"]
                    content = self._read_artifact(path, artifact)
                    if (
                        struct.unpack_from("<H", content, 0)[0] != 3
                        or struct.unpack_from("<H", content, 16)[0] != family
                    ):
                        raise ValueError("XDB structure/address family mismatch")
                    searchers[family] = xdb.new_with_buffer(
                        xdb_util.IPv4 if family == 4 else xdb_util.IPv6, content
                    )
                self._searchers = searchers
            except (OSError, ValueError, KeyError, struct.error) as error:
                for searcher in searchers.values():
                    searcher.close()
                searchers.clear()
                content = b""
                raise IpException(
                    IpErrorCodes.XDB_LOAD_ERROR, cause=error, context={"path": str(path)}
                ) from error

    @staticmethod
    def _read_artifact(path: Path, artifact: dict) -> bytes:
        artifact_path = path / artifact["filename"]
        if artifact_path.stat().st_size != artifact["bytes"]:
            raise ValueError(f"{artifact['filename']} byte size mismatch")
        content = artifact_path.read_bytes()
        if hashlib.sha256(content).hexdigest() != artifact["sha256"]:
            raise ValueError(f"{artifact['filename']} SHA-256 mismatch")
        return content

    def search(self, ip: str) -> str:
        normalized = ClientIpResolver.normalize_ip(ip)
        if normalized is None:
            raise ValueError("ip 必须是 IPv4 或 IPv6 地址")
        address = ipaddress.ip_address(normalized)
        with self._lock:
            if self._searchers is None:
                raise IpException(IpErrorCodes.NOT_INITIALIZED)
            if address.version not in self._searchers:
                raise IpException(
                    IpErrorCodes.FAMILY_NOT_ENABLED, context={"family": address.version}
                )
            searcher = self._searchers[address.version]
            try:
                return searcher.search(address.packed)
            except (ValueError, IndexError, struct.error, UnicodeError) as error:
                raise IpException(IpErrorCodes.QUERY_FAILED, cause=error) from error

    def close(self) -> None:
        with self._lock:
            if self._searchers is not None:
                for searcher in reversed(self._searchers.values()):
                    searcher.close()
                self._searchers = None
