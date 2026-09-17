class LogRecordConstants:
    """
    日志记录常量 (使用简洁模板语法和 _DIFF 函数)
    """

    # ======================= SYSTEM_USER 用户 =======================
    SYSTEM_USER_TYPE = "SYSTEM 用户"
    SYSTEM_USER_CREATE_SUB_TYPE = "创建用户"
    SYSTEM_USER_CREATE_SUCCESS = "创建了用户【{{ user.nickname }}】"
    SYSTEM_USER_UPDATE_SUB_TYPE = "更新用户"
    SYSTEM_USER_UPDATE_SUCCESS = "更新了用户【{{ user.nickname }}】: {{ diff }}"
    SYSTEM_USER_DELETE_SUB_TYPE = "删除用户"
    SYSTEM_USER_DELETE_SUCCESS = "删除了用户【{{ user.nickname }}】"
    SYSTEM_USER_UPDATE_PASSWORD_SUB_TYPE = "重置用户密码"
    SYSTEM_USER_UPDATE_PASSWORD_SUCCESS = (
        "将用户【{{ user.nickname }}】的密码从【***】重置为【***】"
    )

    # ======================= SYSTEM_ROLE 角色 =======================
    SYSTEM_ROLE_TYPE = "SYSTEM 角色"
    SYSTEM_ROLE_CREATE_SUB_TYPE = "创建角色"
    SYSTEM_ROLE_CREATE_SUCCESS = "创建了角色【{{ role.name }}】"
    SYSTEM_ROLE_UPDATE_SUB_TYPE = "更新角色"
    SYSTEM_ROLE_UPDATE_SUCCESS = "更新了角色【{{ role.name }}】: {{ diff }}"
    SYSTEM_ROLE_DELETE_SUB_TYPE = "删除角色"
    SYSTEM_ROLE_DELETE_SUCCESS = "删除了角色【{{ role.name }}】"
