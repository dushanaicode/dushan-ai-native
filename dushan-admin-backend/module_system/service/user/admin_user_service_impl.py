from __future__ import annotations

from datetime import datetime, timezone
from typing import Collection, override

from framework.common.dates import DateUtils
from framework.common.enums import StatusEnum
from framework.common.exception import ServiceException
from framework.common.page import PageResult
from framework.starter_database.public import (
    transactional,
)
from framework.starter_di.public import (
    Inject,
    get_bean,
    service,
)
from framework.starter_security.public import (
    BizLogService,
    LogRecordContext,
    LogRecordSpec,
    PasswordEncoder,
    SecuritySettings,
    log_record,
)
from module_system.config.system_settings import SystemSettings
from module_system.controller.admin.auth.vo.auth_register_req_vo import AuthRegisterReqVO
from module_system.controller.admin.user.vo.profile.profile_update_req_vo import (
    UserProfileUpdateReqVO,
)
from module_system.controller.admin.user.vo.user.user_import_excel_vo import UserImportExcelVO
from module_system.controller.admin.user.vo.user.user_import_resp_vo import UserImportRespVO
from module_system.controller.admin.user.vo.user.user_page_req_vo import UserPageReqVO
from module_system.controller.admin.user.vo.user.user_save_req_vo import UserSaveReqVO
from module_system.convert.user.user_convert import UserConvert
from module_system.dal.dataobject.tenant.tenant_do import TenantDO
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO
from module_system.dal.mapper.dept.dept_user_post_mapper import DeptUserPostMapper
from module_system.dal.mapper.user.admin_user_mapper import AdminUserMapper
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.definitions.constants.log_record_constants import LogRecordConstants
from module_system.definitions.enums.common.common_sex_enum import CommonSexEnum
from module_system.framework.notification.model.notification_recipient import NotificationRecipient
from module_system.service.dept.dept_service import DeptService
from module_system.service.dept.post_service import PostService
from module_system.service.permission.authorization_revision_service import (
    AuthorizationRevisionService,
)
from module_system.service.permission.permission_cache_service import (
    PermissionCacheService,
)
from module_system.service.permission.permission_service import PermissionService
from module_system.service.tenant.handler.function_tenant_info_handler import (
    FunctionTenantInfoHandler,
)
from module_system.service.tenant.tenant_service import TenantService
from module_system.service.user.admin_user_service import AdminUserService


@service(interface=AdminUserService)
class AdminUserServiceImpl(AdminUserService):
    log_context: LogRecordContext = Inject()
    user_mapper: AdminUserMapper = Inject()
    password_encoder: PasswordEncoder = Inject()
    user_post_mapper: DeptUserPostMapper = Inject()
    tenant_service: TenantService = Inject()
    permission_service: PermissionService = Inject()
    dept_service: DeptService = Inject()
    post_service: PostService = Inject()
    date_utils: DateUtils = Inject()
    permission_cache: PermissionCacheService = Inject()
    settings: SystemSettings = Inject()
    security_settings: SecuritySettings = Inject()
    revisions: AuthorizationRevisionService = Inject()

    @log_record(
        LogRecordSpec(
            sub_type=LogRecordConstants.SYSTEM_USER_CREATE_SUB_TYPE,
            biz_no="{{ user.id }}",
            success=LogRecordConstants.SYSTEM_USER_CREATE_SUCCESS,
            type=LogRecordConstants.SYSTEM_USER_TYPE,
            capture=(),
        )
    )
    @override
    @transactional
    async def create_user(self, create_req_vo: UserSaveReqVO) -> int:
        await self.revisions.advance()
        handler = FunctionTenantInfoHandler(lambda tenant: self._check_account_count(tenant))
        await self.tenant_service.handle_tenant_info(handler)
        await self._validate_user_for_create_or_update(
            id=None,
            username=create_req_vo.username,
            mobile=create_req_vo.mobile,
            email=create_req_vo.email,
            dept_id=create_req_vo.dept_id,
            post_ids=create_req_vo.post_ids,
        )
        user = AdminUserDO(**create_req_vo.model_dump(by_alias=False))
        user.status = StatusEnum.ENABLE.code
        user.password = await self._encode_password(create_req_vo.password)
        await self.user_mapper.insert(user)
        if user.post_ids:
            await self._insert_user_posts(user.id, user.post_ids)
        await self.permission_cache.invalidate_user_caches()
        if self.security_settings.bizlog_enabled:
            self.log_context.put("user", {"id": user.id, "nickname": user.nickname})
        return user.id

    @override
    @transactional
    async def register_user(self, register_req_vo: AuthRegisterReqVO) -> int:
        await self.revisions.advance()
        if not self.settings.user_register_enabled:
            raise ServiceException(ErrorCodeConstants.USER_REGISTER_DISABLED)
        handler = FunctionTenantInfoHandler(lambda tenant: self._check_account_count(tenant))
        await self.tenant_service.handle_tenant_info(handler)
        await self._validate_user_for_create_or_update(
            id=None,
            username=register_req_vo.username,
            mobile=None,
            email=None,
            dept_id=None,
            post_ids=None,
        )
        user = AdminUserDO(
            username=register_req_vo.username,
            nickname=register_req_vo.nickname,
            dept_id=None,
            post_ids=[],
        )
        user.status = StatusEnum.ENABLE.code
        user.password = await self._encode_password(register_req_vo.password)
        await self.user_mapper.insert(user)
        return user.id

    @log_record(
        LogRecordSpec(
            sub_type=LogRecordConstants.SYSTEM_USER_UPDATE_SUB_TYPE,
            biz_no="{{ user.id }}",
            success=LogRecordConstants.SYSTEM_USER_UPDATE_SUCCESS,
            type=LogRecordConstants.SYSTEM_USER_TYPE,
            capture=(),
        )
    )
    @override
    @transactional
    async def update_user(self, update_req_vo: UserSaveReqVO) -> None:
        await self.revisions.advance()
        update_req_vo.password = None
        user = await self._validate_user_for_create_or_update(
            id=update_req_vo.id,
            username=update_req_vo.username,
            mobile=update_req_vo.mobile,
            email=update_req_vo.email,
            dept_id=update_req_vo.dept_id,
            post_ids=update_req_vo.post_ids,
        )
        old_user_vo = UserConvert.convert_do_to_save_vo(user)
        if self.security_settings.bizlog_enabled:
            self.log_context.put("user", {"id": user.id, "nickname": user.nickname})
        update_obj = AdminUserDO(
            **update_req_vo.model_dump(exclude_unset=True, exclude={"password"}, by_alias=False)
        )
        await self.user_mapper.update_by_id(update_obj)
        await self._update_user_post(update_req_vo, update_obj)
        if self.security_settings.bizlog_enabled:
            await get_bean(BizLogService).record_diff(
                old_user_vo,
                update_req_vo,
                formatters=(
                    ("get_dept_by_id", self._dept_label),
                    ("get_post_by_id", self._post_label),
                    ("get_sex", self._sex_label),
                ),
            )
        old_dept_id = getattr(user, "dept_id", None)
        new_dept_id = getattr(update_obj, "dept_id", None)
        if old_dept_id != new_dept_id:
            await self.permission_cache.invalidate_user_caches()

    @override
    @transactional
    async def update_user_login(self, id: int, login_ip: str) -> None:
        update_obj = AdminUserDO(
            id=id, login_ip=login_ip, login_date=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        await self.user_mapper.update_by_id(update_obj)

    @override
    @transactional
    async def update_user_profile(self, id: int, req_vo: UserProfileUpdateReqVO) -> None:
        await self.revisions.advance()
        await self._validate_user_exists(id)
        await self._validate_email_unique(id, req_vo.email)
        await self._validate_mobile_unique(id, req_vo.mobile)
        update_obj = UserConvert.convert_update_req_to_admin_user(id, req_vo)
        if update_obj:
            await self.user_mapper.update_by_id(update_obj)

    @log_record(
        LogRecordSpec(
            sub_type=LogRecordConstants.SYSTEM_USER_UPDATE_PASSWORD_SUB_TYPE,
            biz_no="{{ user.id }}",
            success=LogRecordConstants.SYSTEM_USER_UPDATE_PASSWORD_SUCCESS,
            type=LogRecordConstants.SYSTEM_USER_TYPE,
            capture=(),
        )
    )
    @override
    @transactional
    async def update_user_password(self, id: int, password: str) -> None:
        await self.revisions.advance()
        user = await self._validate_user_exists(id)
        await self.change_password(id, password)
        if self.security_settings.bizlog_enabled:
            self.log_context.put("user", {"id": user.id, "nickname": user.nickname})

    @log_record(
        LogRecordSpec(
            sub_type=LogRecordConstants.SYSTEM_USER_DELETE_SUB_TYPE,
            biz_no="{{ user.id }}",
            success=LogRecordConstants.SYSTEM_USER_DELETE_SUCCESS,
            type=LogRecordConstants.SYSTEM_USER_TYPE,
            capture=(),
        )
    )
    @override
    @transactional
    async def delete_user(self, id: int) -> None:
        await self.revisions.advance()
        user = await self._validate_user_exists(id)
        await self.user_mapper.delete_by_id(id)
        await self.permission_service.process_user_deleted(id)
        await self.user_post_mapper.delete_by_user_id(id)
        await self.permission_cache.invalidate_user_caches()
        if self.security_settings.bizlog_enabled:
            self.log_context.put("user", {"id": user.id, "nickname": user.nickname})

    @override
    @transactional
    async def delete_user_batch(self, ids: list[int]) -> int:
        await self.revisions.advance()
        deleted_count = 0
        for user_id in ids:
            await self.delete_user(user_id)
            deleted_count += 1
        return deleted_count

    @override
    async def get_user_by_username(self, username: str) -> AdminUserDO | None:
        return await self.user_mapper.select_by_username(username)

    @override
    async def get_user_by_mobile(self, mobile: str) -> AdminUserDO | None:
        return await self.user_mapper.select_by_mobile(mobile)

    @override
    async def get_user_page(self, req_vo: UserPageReqVO) -> PageResult[AdminUserDO]:
        user_ids = None
        if req_vo.role_id is not None:
            user_ids = await self.permission_service.get_user_role_id_list_by_role_id(
                {req_vo.role_id}
            )
        dept_condition = await self._get_dept_condition(req_vo.dept_id)
        return await self.user_mapper.select_page(req_vo, dept_condition, user_ids)

    @override
    async def get_user(self, id: int) -> AdminUserDO | None:
        return await self.user_mapper.select_by_id(id)

    @override
    async def get_user_list_by_dept_ids(self, dept_ids: Collection[int]) -> list[AdminUserDO]:
        if not dept_ids:
            return []
        return await self.user_mapper.select_list_by_dept_ids(dept_ids)

    @override
    async def get_user_list_by_post_ids(self, post_ids: Collection[int]) -> list[AdminUserDO]:
        if not post_ids:
            return []
        db_user_posts = await self.user_post_mapper.select_list_by_post_ids(post_ids)
        user_ids = {up.user_id for up in db_user_posts}
        if not user_ids:
            return []
        return await self.user_mapper.select_batch_ids(user_ids)

    @override
    async def get_user_list(self, ids: Collection[int]) -> list[AdminUserDO]:
        if not ids:
            return []
        return await self.user_mapper.select_batch_ids(ids)

    @override
    async def validate_user_list(self, ids: Collection[int]) -> None:
        if not ids:
            return
        users = await self.user_mapper.select_batch_ids(ids)
        user_map = {user.id: user for user in users}
        for id in ids:
            user = user_map.get(id)
            if user is None:
                raise ServiceException(ErrorCodeConstants.USER_NOT_EXISTS)
            if user.status != StatusEnum.ENABLE.code:
                raise ServiceException(ErrorCodeConstants.USER_NOT_EXISTS, user.nickname)

    @override
    async def get_user_list_by_nickname(self, nickname: str) -> list[AdminUserDO]:
        return await self.user_mapper.select_list_by_nickname(nickname)

    @override
    async def is_password_match(self, raw_password: str, encoded_password: str) -> bool:
        return await self.password_encoder.verify(raw_password, encoded_password)

    @override
    @transactional
    async def import_user_list(
        self, import_users: list[UserImportExcelVO], is_update_support: bool
    ) -> UserImportRespVO:
        await self.revisions.advance()
        if not import_users:
            raise ServiceException(ErrorCodeConstants.USER_IMPORT_LIST_IS_EMPTY)
        init_password = (
            None
            if self.settings.default_password is None
            else self.settings.default_password.get_secret_value()
        )
        if not init_password:
            raise ServiceException(ErrorCodeConstants.USER_IMPORT_INIT_PASSWORD)
        resp_vo = UserImportRespVO(create_usernames=[], update_usernames=[], failure_usernames={})
        for import_user in import_users:
            try:
                user_save_vo = UserSaveReqVO(**import_user.model_dump(by_alias=False))
                user_save_vo.password = init_password
            except Exception as ex:
                resp_vo.failure_usernames[import_user.username] = str(ex)
                continue
            try:
                await self._validate_user_for_create_or_update(
                    id=None,
                    username=None,
                    mobile=import_user.mobile,
                    email=import_user.email,
                    dept_id=import_user.dept_id,
                    post_ids=None,
                )
            except ServiceException as ex:
                resp_vo.failure_usernames[import_user.username] = ex.msg
                continue
            exist_user = await self.user_mapper.select_by_username(import_user.username)
            if exist_user is None:
                new_user = AdminUserDO(**import_user.model_dump(by_alias=False))
                new_user.password = await self._encode_password(init_password)
                new_user.post_ids = []
                await self.user_mapper.insert(new_user)
                resp_vo.create_usernames.append(import_user.username)
            else:
                if not is_update_support:
                    resp_vo.failure_usernames[import_user.username] = "用户已存在"
                    continue
                update_user = AdminUserDO(**import_user.model_dump(by_alias=False))
                update_user.id = exist_user.id
                await self.user_mapper.update_by_id(update_user)
                resp_vo.update_usernames.append(import_user.username)
        return resp_vo

    @override
    async def get_user_list_by_status(self, status: int) -> list[AdminUserDO]:
        return await self.user_mapper.select_list_by_status(status)

    @override
    async def get_user_count(self) -> int:
        return await self.user_mapper.select_count()

    @override
    async def get_user_info_list_by_ids(self, ids: list[int]) -> list[NotificationRecipient]:
        if not ids:
            return []
        users = await self.user_mapper.select_batch_ids(ids)
        return [
            NotificationRecipient(
                id=user.id, email=user.email, mobile=user.mobile, nickname=user.nickname
            )
            for user in users
        ]

    @override
    async def search_by_keyword(self, keyword: str, limit: int = 20) -> list[AdminUserDO]:
        return await self.user_mapper.select_by_keyword(keyword, limit)

    async def _encode_password(self, password: str) -> str:
        return await self.password_encoder.hash(password)

    async def _validate_user_exists(self, id: int) -> AdminUserDO:
        if id is None:
            raise ServiceException(ErrorCodeConstants.USER_NOT_EXISTS)
        user = await self.user_mapper.select_by_id(id)
        if user is None:
            raise ServiceException(ErrorCodeConstants.USER_NOT_EXISTS)
        return user

    async def _validate_user_for_create_or_update(
        self,
        id: int | None,
        username: str | None,
        mobile: str | None,
        email: str | None,
        dept_id: int | None,
        post_ids: set[int] | None,
    ) -> AdminUserDO:
        user = await self._validate_user_exists(id) if id is not None else AdminUserDO()
        await self._validate_username_unique(id, username)
        await self._validate_email_unique(id, email)
        await self._validate_mobile_unique(id, mobile)
        await self._validate_dept_list(dept_id)
        await self._validate_post_list(post_ids)
        return user

    async def _validate_dept_list(self, id: int) -> None:
        if not id:
            return
        dept = await self.dept_service.get_dept(id)
        if dept is None:
            raise ServiceException(ErrorCodeConstants.DEPT_NOT_FOUND)
        if dept.status != StatusEnum.ENABLE.code:
            raise ServiceException(ErrorCodeConstants.DEPT_NOT_ENABLE, dept.name)

    async def _validate_post_list(self, ids: Collection[int]) -> None:
        if not ids:
            return
        posts = await self.post_service.get_post_list(ids)
        post_map = {post.id: post for post in posts}
        for pid in ids:
            post = post_map.get(pid)
            if post is None:
                raise ServiceException(ErrorCodeConstants.POST_NOT_FOUND)
            if post.status != StatusEnum.ENABLE.code:
                raise ServiceException(ErrorCodeConstants.POST_NOT_ENABLE, post.name)

    async def _validate_username_unique(self, id: int | None, username: str | None) -> None:
        if not username:
            return
        user = await self.user_mapper.select_by_username(username)
        if user and (id is None or user.id != id):
            raise ServiceException(ErrorCodeConstants.USER_USERNAME_EXISTS, username)

    async def _validate_email_unique(self, id: int | None, email: str | None) -> None:
        if not email:
            return
        user = await self.user_mapper.select_by_email(email)
        if user and (id is None or user.id != id):
            raise ServiceException(ErrorCodeConstants.USER_EMAIL_EXISTS, email)

    async def _validate_mobile_unique(self, id: int | None, mobile: str | None) -> None:
        if not mobile:
            return
        user = await self.user_mapper.select_by_mobile(mobile)
        if user and (id is None or user.id != id):
            raise ServiceException(ErrorCodeConstants.USER_MOBILE_EXISTS, mobile)

    async def _validate_old_password(self, id: int, old_password: str) -> None:
        user = await self.user_mapper.select_by_id(id)
        if not user or not await self.is_password_match(old_password, user.password):
            raise ServiceException(ErrorCodeConstants.USER_PASSWORD_FAILED)

    async def _update_user_post(self, req_vo: UserSaveReqVO, update_obj: AdminUserDO) -> None:
        user_id = req_vo.id
        db_user_posts = await self.user_post_mapper.select_list_by_user_id(user_id)
        db_post_ids = {item.post_id for item in db_user_posts}
        updated_post_ids = set(update_obj.post_ids or [])
        create_post_ids = updated_post_ids - db_post_ids
        delete_post_ids = db_post_ids - updated_post_ids
        if create_post_ids:
            await self._insert_user_posts(user_id, create_post_ids)
        if delete_post_ids:
            await self.user_post_mapper.delete_by_user_id_and_post_id(
                user_id, list(delete_post_ids)
            )

    async def _get_dept_condition(self, dept_id: int | None) -> set[int]:
        if dept_id is None:
            return set()
        child_depts = await self.dept_service.get_child_dept_list(dept_id)
        dept_ids = {dept.id for dept in child_depts}
        dept_ids.add(dept_id)
        return dept_ids

    async def _check_account_count(self, tenant: TenantDO) -> None:
        count = await self.user_mapper.select_count()
        if count >= tenant.account_count:
            raise ServiceException(ErrorCodeConstants.USER_COUNT_MAX, tenant.account_count)

    async def _insert_user_posts(self, user_id: int, post_ids: Collection[int]) -> None:
        """批量插入用户岗位关联"""
        await self.user_post_mapper.insert_batch_by_user_id(user_id, post_ids)

    @transactional
    async def change_password(self, user_id: int, password: str):
        await self._validate_user_exists(user_id)
        await self.user_mapper.update_by_condition(
            {
                "password": await self.password_encoder.hash(password),
                "credential_revision": AdminUserDO.credential_revision + 1,
            },
            AdminUserDO.id == user_id,
        )

    @transactional
    async def update_user_password_by_vo(self, id, req_vo):
        await self._validate_old_password(id, req_vo.old_password)
        await self.change_password(id, req_vo.new_password)

    @transactional
    async def update_user_status(self, id, status):
        await self._validate_user_exists(id)
        StatusEnum.from_code(status)
        await self.user_mapper.update_by_condition(
            {"status": status, "credential_revision": AdminUserDO.credential_revision + 1},
            AdminUserDO.id == id,
        )
        await self.revisions.advance()

    async def _dept_label(self, value):
        item = await self.dept_service.get_dept(int(value))
        return "" if item is None else item.name

    async def _post_label(self, value):
        item = await self.post_service.get_post(int(value))
        return "" if item is None else item.name

    @staticmethod
    def _sex_label(value):
        return CommonSexEnum.from_code(value).label
