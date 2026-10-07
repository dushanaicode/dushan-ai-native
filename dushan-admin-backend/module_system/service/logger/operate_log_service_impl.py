from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import override

from framework.common.page import PageResult
from framework.starter_database.public import (
    SessionProvider,
    transactional,
)
from framework.starter_di.public import (
    Inject,
    service,
)
from framework.starter_ip.config.ip_settings import IpSettings
from framework.starter_ip.public import IpLocationService
from framework.starter_security.public import (
    LogRecordReservation,
)
from module_system.api.logger.dto.operate_log_create_req_dto import OperateLogCreateReqDTO
from module_system.api.logger.dto.operate_log_page_req_dto import OperateLogPageReqDTO
from module_system.controller.admin.logger.vo.operate_log.operate_log_page_req_vo import (
    OperateLogPageReqVO,
)
from module_system.dal.dataobject.logger.operate_log_do import OperateLogDO
from module_system.dal.mapper.logger.operate_log_mapper import OperateLogMapper
from module_system.dal.mapper.user.admin_user_mapper import AdminUserMapper
from module_system.service.logger.operate_log_service import OperateLogService


@service(interface=OperateLogService)
class OperateLogServiceImpl(OperateLogService):
    """操作日志服务实现类"""

    operate_log_mapper: OperateLogMapper = Inject()
    users: AdminUserMapper = Inject()
    ip_locations: IpLocationService = Inject()
    ip_settings: IpSettings = Inject()

    @override
    @transactional
    async def create_operate_log(self, req_dto: OperateLogCreateReqDTO) -> None:
        operate_log = OperateLogDO(**req_dto.model_dump(by_alias=False))
        await self.operate_log_mapper.insert(operate_log)

    @override
    async def get_operate_log_page_vo(self, req: OperateLogPageReqVO) -> PageResult[OperateLogDO]:
        return await self.operate_log_mapper.select_page_vo(req)

    @override
    async def get_operate_log_page_dto(self, req: OperateLogPageReqDTO) -> PageResult[OperateLogDO]:
        return await self.operate_log_mapper.select_page_dto(req)

    database: SessionProvider = Inject()

    @transactional(propagation="requires_new")
    async def reserve(self, operation):
        request = operation.request
        user = await self.users.select_by_id(int(operation.identity.principal_id))
        user_info = (
            {}
            if user is None
            else {
                "username": user.username,
                "nickname": user.nickname,
                "dept_id": None if user.dept_id is None else str(user.dept_id),
            }
        )
        if request is not None and request.user_ip:
            if self.ip_settings.enabled:
                location = await self.ip_locations.lookup(request.user_ip)
                user_info.update(location=location.location, location_status=location.status)
            else:
                user_info["location_status"] = "disabled"
        entry = OperateLogDO(
            event_id=operation.event_id,
            result="pending",
            duration_ms=None,
            lease_until=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5),
            trace_id=operation.trace_id or "",
            user_id=int(operation.identity.principal_id),
            user_type=2,
            type=operation.type,
            sub_type=operation.sub_type,
            biz_id=0,
            action="",
            extra="",
            user_info=user_info,
            request_method="" if request is None else request.request_method,
            request_url="" if request is None else request.request_url,
            user_ip="" if request is None else request.user_ip or "",
            user_agent="" if request is None else request.user_agent or "",
        )
        await self.operate_log_mapper.insert(entry)
        return LogRecordReservation(
            event_id=operation.event_id, persistent=True, handle=str(entry.id)
        )

    @transactional(propagation="requires_new")
    async def finalize(self, reservation, entry):
        await self.operate_log_mapper.update_by_condition(
            {
                "result": entry.result,
                "duration_ms": entry.duration_ms,
                "biz_id": 0 if entry.biz_no is None else int(entry.biz_no),
                "action": entry.action,
                "extra": entry.extra or "",
                "lease_until": None,
            },
            OperateLogDO.id == int(reservation.handle),
            OperateLogDO.event_id == reservation.event_id,
        )

    @transactional(propagation="requires_new")
    async def renew(self, reservation):
        await self.operate_log_mapper.update_by_condition(
            {"lease_until": datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5)},
            OperateLogDO.id == int(reservation.handle),
            OperateLogDO.event_id == reservation.event_id,
            OperateLogDO.result == "pending",
        )

    @transactional(propagation="requires_new")
    async def cancel(self, reservation):
        await self.operate_log_mapper.update_by_condition(
            {"result": "cancelled", "lease_until": None},
            OperateLogDO.id == int(reservation.handle),
            OperateLogDO.event_id == reservation.event_id,
            OperateLogDO.result == "pending",
        )
