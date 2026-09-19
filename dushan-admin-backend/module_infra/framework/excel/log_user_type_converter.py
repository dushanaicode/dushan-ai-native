from framework.common.enums import UserTypeEnum


class LogUserTypeConverter:
    async def to_excel(self, value, context):
        return "未登录" if value == 0 else UserTypeEnum.from_code(value).label

    async def to_python(self, value, context):
        if value == "未登录":
            return 0
        member = UserTypeEnum.get_by_label(value)
        if member is None:
            raise ValueError("用户类型标签不存在")
        return member.code
