from module_system.controller.admin.dept.vo.dept.dept_simple_resp_vo import DeptSimpleRespVO
from module_system.controller.admin.dept.vo.post.post_simple_resp_vo import PostSimpleRespVO
from module_system.controller.admin.permission.vo.role.role_simple_resp_vo import RoleSimpleRespVO
from module_system.controller.admin.user.vo.profile.user_profile_resp_vo import UserProfileRespVO
from module_system.controller.admin.user.vo.user.user_import_excel_vo import UserImportExcelVO
from module_system.controller.admin.user.vo.user.user_resp_vo import UserRespVO
from module_system.controller.admin.user.vo.user.user_save_req_vo import UserSaveReqVO
from module_system.controller.admin.user.vo.user.user_simple_resp_vo import UserSimpleRespVO
from module_system.dal.cache.permission.dto.role_cache_dto import RoleCacheDTO
from module_system.dal.dataobject.dept.dept_do import DeptDO
from module_system.dal.dataobject.dept.post_do import PostDO
from module_system.dal.dataobject.user.admin_user_do import AdminUserDO
from module_system.dal.dataobject.user.admin_user_profile_do import AdminUserProfileDO


class UserConvert:
    @staticmethod
    def convert_list(user_list: list[AdminUserDO], dept_map: dict[int, DeptDO]) -> list[UserRespVO]:
        """将 AdminUserDO 的列表转换为 UserRespVO 的列表"""
        return [UserConvert.convert(user, dept_map.get(user.dept_id)) for user in user_list]

    @staticmethod
    def convert(user: AdminUserDO, dept: DeptDO | None) -> UserRespVO:
        """将单个 AdminUserDO 转换为 UserRespVO"""
        vo = UserRespVO.model_validate(user)
        vo.dept_name = dept.name if dept is not None else None
        return vo

    @staticmethod
    def convert_simple_list(
        user_list: list[AdminUserDO], dept_map: dict[int, DeptDO]
    ) -> list[UserSimpleRespVO]:
        """将 AdminUserDO 的列表转换为 UserSimpleRespVO 的列表"""
        result = []
        for user in user_list:
            dept = dept_map.get(user.dept_id)
            vo = UserSimpleRespVO.model_validate(user)
            vo.dept_name = dept.name if dept is not None else None
            result.append(vo)
        return result

    @staticmethod
    def convert_import_to_save_vo(
        import_user: UserImportExcelVO, init_password: str
    ) -> UserSaveReqVO:
        """按导入白名单构造保存请求，将已解码的部门编号还原为请求输入。"""
        values = import_user.to_write_dict(
            fields={"username", "nickname", "dept_id", "email", "mobile", "sex"},
            exclude_unset=False,
        )
        if values["dept_id"] is not None:
            values["dept_id"] = str(values["dept_id"])
        return UserSaveReqVO(**values, password=init_password)

    @staticmethod
    def convert_profile(
        user: AdminUserDO,
        user_roles: list[RoleCacheDTO],
        dept: DeptDO | None,
        posts: list[PostDO],
        profile: AdminUserProfileDO | None = None,
    ) -> UserProfileRespVO:
        """将 AdminUserDO 对象及其关联的角色、部门、岗位等信息转换为 UserProfileRespVO"""
        return UserProfileRespVO(
            id=user.id,
            username=user.username,
            nickname=user.nickname,
            email=user.email,
            mobile=user.mobile,
            sex=user.sex,
            avatar=user.avatar,
            login_ip=user.login_ip,
            login_date=user.login_date,
            create_time=user.create_time,
            roles=[RoleSimpleRespVO(id=role.id, name=role.name) for role in user_roles],
            dept=DeptSimpleRespVO(id=dept.id, name=dept.name, parent_id=dept.parent_id)
            if dept
            else None,
            posts=[PostSimpleRespVO.model_validate(post) for post in posts],
            bio=profile.bio if profile else None,
            tags=profile.tags if profile else None,
            address=profile.address if profile else None,
            skills=profile.skills if profile else None,
            work_scope=profile.work_scope if profile else None,
            expertise=profile.expertise if profile else None,
            communication_style=profile.communication_style if profile else None,
            ai_preference=profile.ai_preference if profile else None,
        )

    @staticmethod
    def convert_do_to_save_vo(user_do: AdminUserDO | None) -> UserSaveReqVO | None:
        """将 AdminUserDO 转换为 UserSaveReqVO"""
        if not user_do:
            return None
        values = {name: getattr(user_do, name) for name in UserSaveReqVO.model_fields}
        # 数据库用空串表示未设置的联系方式，审计快照沿用请求模型的 None 语义。
        for name in ("email", "mobile"):
            values[name] = values[name] or None
        values["password"] = None
        for name in ("id", "dept_id"):
            if values[name] is not None:
                values[name] = str(values[name])
        if values["post_ids"] is not None:
            values["post_ids"] = [str(value) for value in values["post_ids"]]
        return UserSaveReqVO.model_validate(values)
