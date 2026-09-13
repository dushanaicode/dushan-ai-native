import asyncio
import ipaddress
from collections import OrderedDict
from contextvars import Context
from functools import partial
from time import monotonic

from loguru import logger

from framework.starter_di.decorators.components import service
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_ip.config.ip_settings import IpSettings
from framework.starter_ip.core.client_ip_resolver import ClientIpResolver
from framework.starter_ip.exception.ip_address_family_not_enabled import IpAddressFamilyNotEnabled
from framework.starter_ip.exception.ip_error_code_constants import IpErrorCodeConstants
from framework.starter_ip.exception.ip_exception import IpException
from framework.starter_ip.exception.ip_provider_error import IpProviderError
from framework.starter_ip.model.inflight_ip_query import InflightIpQuery
from framework.starter_ip.model.ip_location import IpLocation
from framework.starter_ip.spi.ip_location_provider import IpLocationProvider


@service(scope=ComponentScopeEnum.SINGLETON)
class IpLocationService:
    """本地优先、应用内冷查询合并；服务关闭先等待自己拥有的查询终态。"""

    def __init__(self, settings: IpSettings, providers: list[IpLocationProvider]) -> None:
        self._settings = settings
        self._providers = providers
        self._active: tuple[IpLocationProvider, ...] = ()
        self._cache: OrderedDict[str, tuple[float, IpLocation]] = OrderedDict()
        self._inflight: dict[str, InflightIpQuery] = {}
        self._close_task: asyncio.Task[None] | None = None
        self._private_networks = tuple(
            ipaddress.ip_network(cidr)
            for cidr in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7")
        )
        self._opened = False

    def open(self) -> None:
        if self._opened or self._close_task is not None:
            raise RuntimeError("IP 查询服务不能重复打开")
        by_name = {provider.name: provider for provider in self._providers}
        if len(by_name) != len(self._providers):
            raise ValueError("IP Provider 名称重复")
        active = []
        if self._settings.local_enabled:
            active.extend(
                sorted(
                    (provider for provider in self._providers if not provider.online),
                    key=lambda provider: provider.name,
                )
            )
        if self._settings.online_enabled:
            for name in self._settings.online_providers:
                if name not in by_name or not by_name[name].online:
                    raise ValueError(f"在线 IP Provider 未注册: {name}")
                active.append(by_name[name])
        self._active = tuple(active)
        self._opened = True

    async def lookup(self, ip: str) -> IpLocation:
        if not self._opened:
            raise IpException(IpErrorCodeConstants.NOT_INITIALIZED)
        normalized = ClientIpResolver.normalize_ip(ip)
        if normalized is None:
            raise ValueError("ip 必须是 IPv4 或 IPv6 地址")
        special = self._non_public_location(normalized)
        if special is not None:
            return special
        cached = self._cache.get(normalized)
        if cached is not None:
            if cached[0] > monotonic():
                self._cache.move_to_end(normalized)
                return cached[1]
            self._cache.pop(normalized)
        deadline = asyncio.get_running_loop().time() + self._settings.query_budget_seconds
        timeout = asyncio.timeout_at(deadline)
        try:
            async with timeout:
                return await self._join_query(normalized, deadline)
        except TimeoutError:
            if not timeout.expired():
                raise
            return self._budget_exceeded(normalized, [])

    async def _join_query(self, ip: str, deadline: float) -> IpLocation:
        while self._opened:
            flight = self._inflight.get(ip)
            if flight is not None and not flight.task.done() and not flight.waiters:
                # 无等待者的旧查询正在取消清理，终态之前不为同 IP 启动第二轮。
                await asyncio.wait((flight.task,))
                continue
            if flight is None or flight.task.done():
                task = asyncio.create_task(
                    self._query_and_cache(ip, deadline), name="ip-location-query", context=Context()
                )
                timer = asyncio.get_running_loop().call_at(
                    deadline, self._expire_query, ip, task, context=Context()
                )
                flight = InflightIpQuery(task, timer)
                self._inflight[ip] = flight
                task.add_done_callback(
                    partial(self._query_completed, ip, flight), context=Context()
                )
            flight.waiters += 1
            try:
                return await asyncio.shield(flight.task)
            except asyncio.CancelledError:
                if not self._opened and not asyncio.current_task().cancelling():
                    raise IpException(IpErrorCodeConstants.NOT_INITIALIZED) from None
                raise
            except Exception:
                flight.error_observed = True
                raise
            finally:
                flight.waiters -= 1
                if not flight.waiters:
                    self._cancel_query(flight, "IP 查询没有剩余等待者")
                self._report_unobserved_error(flight)
        raise IpException(IpErrorCodeConstants.NOT_INITIALIZED)

    def _query_completed(self, ip: str, flight: InflightIpQuery, task: asyncio.Task) -> None:
        flight.deadline_timer.cancel()
        if self._inflight.get(ip) is flight:
            self._inflight.pop(ip)
        self._report_unobserved_error(flight)

    def _expire_query(self, ip: str, task: asyncio.Task) -> None:
        flight = self._inflight.get(ip)
        if flight is not None and flight.task is task:
            flight.budget_expired = True
            self._cancel_query(flight, "IP 查询总预算耗尽")

    @staticmethod
    def _cancel_query(flight: InflightIpQuery, reason: str) -> None:
        # 第一次取消就撤销预算定时器，避免它再次取消 Provider 的清理 await。
        flight.deadline_timer.cancel()
        if not flight.task.done() and not flight.task.cancelling():
            flight.task.cancel(reason)

    @staticmethod
    def _report_unobserved_error(flight: InflightIpQuery) -> None:
        if (
            flight.waiters
            or flight.error_observed
            or not flight.task.done()
            or flight.task.cancelled()
        ):
            return
        error = flight.task.exception()
        if error is not None:
            flight.error_observed = True
            logger.opt(exception=error).error("无等待者的 IP 查询失败")

    async def _query_and_cache(self, normalized: str, deadline: float) -> IpLocation:
        result = await self._query(normalized, deadline)
        if not self._opened:
            raise IpException(IpErrorCodeConstants.NOT_INITIALIZED)
        if not self._inflight[normalized].waiters:
            raise asyncio.CancelledError
        ttl = (
            self._settings.unknown_cache_ttl_seconds
            if result.status == "unknown"
            else self._settings.cache_ttl_seconds
        )
        if self._settings.cache_max_size and ttl and result.status != "unavailable":
            self._cache[normalized] = (monotonic() + ttl, result)
            self._cache.move_to_end(normalized)
            while len(self._cache) > self._settings.cache_max_size:
                self._cache.popitem(last=False)
        return result

    def _non_public_location(self, ip: str) -> IpLocation | None:
        address = ipaddress.ip_address(ip)
        if address.is_loopback:
            return IpLocation(ip, "loopback", "回环地址")
        if address.is_link_local:
            return IpLocation(ip, "link_local", "链路本地地址")
        if address.is_private and any(address in network for network in self._private_networks):
            return IpLocation(ip, "private", "内网IP")
        if not address.is_global or address.is_multicast:
            return IpLocation(ip, "reserved", "非公网地址")
        return None

    async def _query(self, ip: str, deadline: float) -> IpLocation:
        if not self._active:
            return IpLocation(ip, "unavailable", None, failures=("no_provider",))
        loop = asyncio.get_running_loop()
        failures: list[str] = []
        try:
            for provider in self._active:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    return self._budget_exceeded(ip, failures)
                try:
                    location = await provider.query(ip, remaining)
                except IpAddressFamilyNotEnabled as error:
                    failures.append(f"{provider.name}:ipv{error.family}_not_enabled")
                    continue
                except IpProviderError as error:
                    if self._settings.online_failure_policy == "raise":
                        raise
                    failures.append(f"{error.provider}:{error.reason}")
                    logger.warning(
                        "IP Provider 不可用: provider={}, reason={}",
                        error.provider,
                        error.reason,
                    )
                    continue
                if loop.time() >= deadline:
                    return self._budget_exceeded(ip, failures)
                if location is not None:
                    return IpLocation(ip, "found", location, provider.name, tuple(failures))
        except asyncio.CancelledError:
            if not self._inflight[ip].budget_expired:
                raise
            return self._budget_exceeded(ip, failures)
        return IpLocation(
            ip, "unavailable" if failures else "unknown", None, failures=tuple(failures)
        )

    def _budget_exceeded(self, ip: str, failures: list[str]) -> IpLocation:
        if self._settings.online_failure_policy == "raise":
            raise IpProviderError("chain", "budget_exceeded")
        return IpLocation(ip, "unavailable", None, failures=(*failures, "chain:budget_exceeded"))

    async def close(self) -> None:
        self._opened = False
        if self._close_task is None:
            self._close_task = asyncio.create_task(
                self._close_queries(), name="ip-location-close", context=Context()
            )
        await asyncio.shield(self._close_task)

    async def _close_queries(self) -> None:
        flights = tuple(self._inflight.values())
        tasks = tuple(flight.task for flight in flights)
        for flight in flights:
            self._cancel_query(flight, "IP 查询服务正在关闭")
        await asyncio.gather(*tasks, return_exceptions=True)
        self._inflight.clear()
        self._active = ()
        self._cache.clear()
