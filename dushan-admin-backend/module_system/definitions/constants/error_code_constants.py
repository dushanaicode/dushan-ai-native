from framework.common.exception import ErrorCode, error_code


@error_code
class ErrorCodeConstants:
    """
    System 错误码枚举类

    system 系统，使用 1-002-000-000 段
    """

    # ========== AUTH 模块 1-002-000-000 ==========
    AUTH_LOGIN_BAD_CREDENTIALS = ErrorCode(
        code=1_002_000_000,
        description="登录失败，账号密码不正确",
        message_key="system.auth.login_bad_credentials",
    )
    AUTH_LOGIN_USER_DISABLED = ErrorCode(
        code=1_002_000_001,
        description="登录失败，账号被禁用",
        message_key="system.auth.login_user_disabled",
    )
    AUTH_LOGIN_CAPTCHA_CODE_ERROR = ErrorCode(
        code=1_002_000_004,
        description="验证码验证失败",
        message_key="system.auth.login_captcha_code_error",
    )
    AUTH_THIRD_LOGIN_NOT_BIND = ErrorCode(
        code=1_002_000_005,
        description="未绑定账号，需要进行绑定",
        message_key="system.auth.third_login_not_bind",
    )
    AUTH_TOKEN_EXPIRED = ErrorCode(
        code=1_002_000_006, description="Token 已经过期", message_key="system.auth.token_expired"
    )
    AUTH_MOBILE_NOT_EXISTS = ErrorCode(
        code=1_002_000_007, description="手机号不存在", message_key="system.auth.mobile_not_exists"
    )
    AUTH_REGISTER_CAPTCHA_CODE_ERROR = ErrorCode(
        code=1_002_000_008,
        description="注册验证码验证失败",
        message_key="system.auth.register_captcha_code_error",
    )
    AUTH_INVALID_TOKEN_CODE = ErrorCode(
        code=1_002_000_009, description="非法令牌格式", message_key="system.auth.invalid_token_code"
    )
    AUTH_TOKEN_NOT_FOUND_CODE = ErrorCode(
        code=1_002_000_010, description="访问令牌不存在", message_key="system.auth.token_not_found"
    )

    # ========== 菜单模块 1-002-001-000 ==========
    MENU_NAME_DUPLICATE = ErrorCode(
        code=1_002_001_000,
        description="已经存在该名字的菜单",
        message_key="system.menu.name_duplicate",
    )
    MENU_PARENT_NOT_EXISTS = ErrorCode(
        code=1_002_001_001, description="父菜单不存在", message_key="system.menu.parent_not_exists"
    )
    MENU_PARENT_ERROR = ErrorCode(
        code=1_002_001_002,
        description="不能设置自己为父菜单",
        message_key="system.menu.parent_error",
    )
    MENU_NOT_EXISTS = ErrorCode(
        code=1_002_001_003, description="菜单不存在", message_key="system.menu.not_exists"
    )
    MENU_EXISTS_CHILDREN = ErrorCode(
        code=1_002_001_004,
        description="存在子菜单，无法删除",
        message_key="system.menu.exists_children",
    )
    MENU_PARENT_NOT_DIR_OR_MENU = ErrorCode(
        code=1_002_001_005,
        description="父菜单的类型必须是目录或者菜单",
        message_key="system.menu.parent_not_dir_or_menu",
    )
    MENU_EXISTS_CHILDREN_MENU = ErrorCode(
        code=1_002_001_006,
        description="存在子菜单，无法删除，请先删除子菜单后重试",
        message_key="system.menu.exists_children_menu",
    )

    # ========== 角色模块 1-002-002-000 ==========
    ROLE_NOT_EXISTS = ErrorCode(
        code=1_002_002_000, description="角色不存在", message_key="system.role.not_exists"
    )
    ROLE_NAME_DUPLICATE = ErrorCode(
        code=1_002_002_001,
        description="已经存在名为【{}】的角色",
        message_key="system.role.name_duplicate",
    )
    ROLE_CODE_DUPLICATE = ErrorCode(
        code=1_002_002_002,
        description="已经存在编码为【{}】的角色",
        message_key="system.role.code_duplicate",
    )
    ROLE_CAN_NOT_UPDATE_SYSTEM_TYPE_ROLE = ErrorCode(
        code=1_002_002_003,
        description="不能操作类型为系统内置的角色",
        message_key="system.role.can_not_update_system_type",
    )
    ROLE_IS_DISABLE = ErrorCode(
        code=1_002_002_004,
        description="名字为【{}】的角色已被禁用",
        message_key="system.role.is_disable",
    )
    ROLE_ADMIN_CODE_ERROR = ErrorCode(
        code=1_002_002_005,
        description="编码【{}】不能使用",
        message_key="system.role.admin_code_error",
    )

    # ========== 用户模块 1-002-003-000 ==========
    USER_USERNAME_EXISTS = ErrorCode(
        code=1_002_003_000,
        description="用户账号已经存在",
        message_key="system.user.username_exists",
    )
    USER_MOBILE_EXISTS = ErrorCode(
        code=1_002_003_001, description="手机号已经存在", message_key="system.user.mobile_exists"
    )
    USER_EMAIL_EXISTS = ErrorCode(
        code=1_002_003_002, description="邮箱已经存在", message_key="system.user.email_exists"
    )
    USER_NOT_EXISTS = ErrorCode(
        code=1_002_003_003, description="用户不存在", message_key="system.user.not_exists"
    )
    USER_IMPORT_LIST_IS_EMPTY = ErrorCode(
        code=1_002_003_004,
        description="导入用户数据不能为空！",
        message_key="system.user.import_list_is_empty",
    )
    USER_PASSWORD_FAILED = ErrorCode(
        code=1_002_003_005,
        description="用户密码校验失败",
        message_key="system.user.password_failed",
    )
    USER_IS_DISABLE = ErrorCode(
        code=1_002_003_006,
        description="名字为【{}】的用户已被禁用",
        message_key="system.user.is_disable",
    )
    USER_TYPE_NOT_EXISTS = ErrorCode(
        code=1_002_003_007, description="无效用户类型", message_key="system.user.type_not_exists"
    )
    USER_COUNT_MAX = ErrorCode(
        code=1_002_003_008,
        description="创建用户失败，原因：超过租户最大租户配额({})！",
        message_key="system.user.count_max",
    )
    USER_IMPORT_INIT_PASSWORD = ErrorCode(
        code=1_002_003_009,
        description="初始密码不能为空",
        message_key="system.user.import_init_password",
    )
    USER_MOBILE_NOT_EXISTS = ErrorCode(
        code=1_002_003_010,
        description="该手机号尚未注册",
        message_key="system.user.mobile_not_exists",
    )
    USER_REGISTER_DISABLED = ErrorCode(
        code=1_002_003_011,
        description="注册功能已关闭",
        message_key="system.user.register_disabled",
    )
    USER_KICKOUT_DEVICE_NOT_OWNER = ErrorCode(
        code=1_002_003_012,
        description="没有权限操作不属于自己的设备",
        message_key="system.user.kickout_device_not_owner",
    )

    # ========== 部门模块 1-002-004-000 ==========
    DEPT_NAME_DUPLICATE = ErrorCode(
        code=1_002_004_000,
        description="已经存在该名字的部门",
        message_key="system.dept.name_duplicate",
    )
    DEPT_PARENT_NOT_EXITS = ErrorCode(
        code=1_002_004_001,
        description="父级部门不存在",
        message_key="system.dept.parent_not_exists",
    )
    DEPT_NOT_FOUND = ErrorCode(
        code=1_002_004_002, description="当前部门不存在", message_key="system.dept.not_found"
    )
    DEPT_EXITS_CHILDREN = ErrorCode(
        code=1_002_004_003,
        description="存在子部门，无法删除",
        message_key="system.dept.exists_children",
    )
    DEPT_PARENT_ERROR = ErrorCode(
        code=1_002_004_004,
        description="不能设置自己为父部门",
        message_key="system.dept.parent_error",
    )
    DEPT_EXISTS_USER = ErrorCode(
        code=1_002_004_005,
        description="部门中存在员工，无法删除",
        message_key="system.dept.exists_user",
    )
    DEPT_NOT_ENABLE = ErrorCode(
        code=1_002_004_006,
        description="部门({})不处于开启状态，不允许选择",
        message_key="system.dept.not_enable",
    )
    DEPT_PARENT_IS_CHILD = ErrorCode(
        code=1_002_004_007,
        description="不能设置自己的子部门为父部门",
        message_key="system.dept.parent_is_child",
    )

    # ========== 岗位模块 1-002-005-000 ==========
    POST_NOT_FOUND = ErrorCode(
        code=1_002_005_000, description="当前岗位不存在", message_key="system.post.not_found"
    )
    POST_NOT_ENABLE = ErrorCode(
        code=1_002_005_001,
        description="岗位({}) 不处于开启状态，不允许选择",
        message_key="system.post.not_enable",
    )
    POST_NAME_DUPLICATE = ErrorCode(
        code=1_002_005_002,
        description="已经存在该名字的岗位",
        message_key="system.post.name_duplicate",
    )
    POST_CODE_DUPLICATE = ErrorCode(
        code=1_002_005_003,
        description="已经存在该标识的岗位",
        message_key="system.post.code_duplicate",
    )

    # ========== 字典类型 1-002-006-000 ==========
    DICT_TYPE_NOT_EXISTS = ErrorCode(
        code=1_002_006_001,
        description="当前字典类型不存在",
        message_key="system.dict_type.not_exists",
    )
    DICT_TYPE_NOT_ENABLE = ErrorCode(
        code=1_002_006_002,
        description="字典类型不处于开启状态，不允许选择",
        message_key="system.dict_type.not_enable",
    )
    DICT_TYPE_NAME_DUPLICATE = ErrorCode(
        code=1_002_006_003,
        description="已经存在该名字的字典类型",
        message_key="system.dict_type.name_duplicate",
    )
    DICT_TYPE_TYPE_DUPLICATE = ErrorCode(
        code=1_002_006_004,
        description="已经存在该类型的字典类型",
        message_key="system.dict_type.type_duplicate",
    )
    DICT_TYPE_HAS_CHILDREN = ErrorCode(
        code=1_002_006_005,
        description="无法删除，该字典类型还有字典数据",
        message_key="system.dict_type.has_children",
    )

    # ========== 字典数据 1-002-007-000 ==========
    DICT_DATA_NOT_EXISTS = ErrorCode(
        code=1_002_007_001,
        description="当前字典数据不存在",
        message_key="system.dict_data.not_exists",
    )
    DICT_DATA_NOT_ENABLE = ErrorCode(
        code=1_002_007_002,
        description="字典数据({})不处于开启状态，不允许选择",
        message_key="system.dict_data.not_enable",
    )
    DICT_DATA_VALUE_DUPLICATE = ErrorCode(
        code=1_002_007_003,
        description="已经存在该值的字典数据",
        message_key="system.dict_data.value_duplicate",
    )

    # ========== 通知公告 1-002-008-000 ==========
    NOTICE_NOT_FOUND = ErrorCode(
        code=1_002_008_001, description="当前通知公告不存在", message_key="system.notice.not_found"
    )
    NOTICE_NOT_ENABLE = ErrorCode(
        code=1_002_008_002, description="当前通知公告已禁用", message_key="system.notice.not_enable"
    )
    NOTICE_CAN_NOT_UPDATE_SYSTEM_TYPE = ErrorCode(
        code=1_002_008_003,
        description="不能操作内置通知模板",
        message_key="system.notice.can_not_update_system_type",
    )
    ANNOUNCEMENT_NOT_FOUND = ErrorCode(
        code=1_002_008_010, description="公告不存在", message_key="system.announcement.not_found"
    )
    ANNOUNCEMENT_STATUS_ERROR = ErrorCode(
        code=1_002_008_011,
        description="公告状态错误",
        message_key="system.announcement.status_error",
    )
    ANNOUNCEMENT_PUBLISH_TIME_REQUIRED = ErrorCode(
        code=1_002_008_012,
        description="定时发布需要设置发布时间",
        message_key="system.announcement.publish_time_required",
    )
    ANNOUNCEMENT_PUBLISH_TIME_INVALID = ErrorCode(
        code=1_002_008_013,
        description="发布时间必须大于当前时间",
        message_key="system.announcement.publish_time_invalid",
    )

    # ========== 短信渠道 1-002-011-000 ==========
    SMS_CHANNEL_NOT_EXISTS = ErrorCode(
        code=1_002_011_000,
        description="短信渠道不存在",
        message_key="system.sms_channel.not_exists",
    )
    SMS_CHANNEL_DISABLE = ErrorCode(
        code=1_002_011_001,
        description="短信渠道不处于开启状态，不允许选择",
        message_key="system.sms_channel.disable",
    )
    SMS_CHANNEL_HAS_CHILDREN = ErrorCode(
        code=1_002_011_002,
        description="无法删除，该短信渠道还有短信模板",
        message_key="system.sms_channel.has_children",
    )
    SMS_SCENE_NOT_FOUND = ErrorCode(
        code=1_002_011_003,
        description="验证码场景【{}】查找不到配置",
        message_key="system.sms_channel.scene_not_found",
    )
    SMS_CHANNEL_CODE_IMMUTABLE = ErrorCode(
        code=1_002_011_004,
        description="短信渠道创建后不能更换厂商，请创建新渠道",
        message_key="system.sms_channel.code_immutable",
    )

    # ========== 短信模板 1-002-012-000 ==========
    SMS_TEMPLATE_NOT_EXISTS = ErrorCode(
        code=1_002_012_000,
        description="短信模板不存在",
        message_key="system.sms_template.not_exists",
    )
    SMS_TEMPLATE_CODE_DUPLICATE = ErrorCode(
        code=1_002_012_001,
        description="已经存在编码为【{}】的短信模板",
        message_key="system.sms_template.code_duplicate",
    )
    SMS_TEMPLATE_API_ERROR = ErrorCode(
        code=1_002_012_002,
        description="短信 API 模板调用失败，原因是：{}",
        message_key="system.sms_template.api_error",
    )
    SMS_TEMPLATE_API_AUDIT_CHECKING = ErrorCode(
        code=1_002_012_003,
        description="短信 API 模版无法使用，原因：审批中",
        message_key="system.sms_template.api_audit_checking",
    )
    SMS_TEMPLATE_API_AUDIT_FAIL = ErrorCode(
        code=1_002_012_004,
        description="短信 API 模版无法使用，原因：审批不通过，{}",
        message_key="system.sms_template.api_audit_fail",
    )
    SMS_TEMPLATE_API_NOT_FOUND = ErrorCode(
        code=1_002_012_005,
        description="短信 API 模版无法使用，原因：模版不存在",
        message_key="system.sms_template.api_not_found",
    )
    SMS_TEMPLATE_API_AUDIT_UNKNOWN = ErrorCode(
        code=1_002_012_006,
        description="短信模板({}) 审核状态({}) 不正确",
        message_key="system.sms_template.api_audit_unknown",
    )
    SMS_TEMPLATE_CAN_NOT_UPDATE_BUILTIN = ErrorCode(
        code=1_002_012_007,
        description="不能操作内置短信模板",
        message_key="system.sms_template.can_not_update_builtin",
    )

    # ========== 短信发送 1-002-013-000 ==========
    SMS_SEND_MOBILE_NOT_EXISTS = ErrorCode(
        code=1_002_013_000,
        description="手机号不存在",
        message_key="system.sms_send.mobile_not_exists",
    )
    SMS_SEND_MOBILE_TEMPLATE_PARAM_MISS = ErrorCode(
        code=1_002_013_001,
        description="模板参数({})缺失",
        message_key="system.sms_send.template_param_miss",
    )
    SMS_SEND_TEMPLATE_NOT_EXISTS = ErrorCode(
        code=1_002_013_002,
        description="短信模板不存在",
        message_key="system.sms_send.template_not_exists",
    )
    SMS_SEND_MOBILE_INVALID = ErrorCode(
        code=1_002_013_003,
        description="手机号格式不正确",
        message_key="system.sms_send.mobile_invalid",
    )

    # ========== 短信验证码 1-002-014-000 ==========
    SMS_CODE_NOT_FOUND = ErrorCode(
        code=1_002_014_000, description="验证码不存在", message_key="system.sms_code.not_found"
    )
    SMS_CODE_EXPIRED = ErrorCode(
        code=1_002_014_001, description="验证码已过期", message_key="system.sms_code.expired"
    )
    SMS_CODE_USED = ErrorCode(
        code=1_002_014_002, description="验证码已使用", message_key="system.sms_code.used"
    )
    SMS_CODE_NOT_CORRECT = ErrorCode(
        code=1_002_014_003, description="验证码不正确", message_key="system.sms_code.not_correct"
    )
    SMS_CODE_EXCEED_SEND_MAXIMUM_QUANTITY_PER_DAY = ErrorCode(
        code=1_002_014_004,
        description="超过每日短信发送数量",
        message_key="system.sms_code.exceed_send_max_per_day",
    )
    SMS_CODE_SEND_TOO_FAST = ErrorCode(
        code=1_002_014_005,
        description="短信发送过于频繁",
        message_key="system.sms_code.send_too_fast",
    )

    # ========== 租户模块 1-002-015-000 ==========
    TENANT_NOT_EXISTS = ErrorCode(
        code=1_002_015_000, description="租户不存在", message_key="system.tenant.not_exists"
    )
    TENANT_DISABLE = ErrorCode(
        code=1_002_015_001,
        description="名字为【{}】的租户已被禁用",
        message_key="system.tenant.disable",
    )
    TENANT_EXPIRE = ErrorCode(
        code=1_002_015_002,
        description="名字为【{}】的租户已过期",
        message_key="system.tenant.expire",
    )
    TENANT_CAN_NOT_UPDATE_SYSTEM = ErrorCode(
        code=1_002_015_003,
        description="系统租户不能进行修改、删除等操作",
        message_key="system.tenant.can_not_update_system",
    )
    TENANT_NAME_DUPLICATE = ErrorCode(
        code=1_002_015_004,
        description="名字为【{}】的租户已存在",
        message_key="system.tenant.name_duplicate",
    )
    TENANT_WEBSITE_DUPLICATE = ErrorCode(
        code=1_002_015_005,
        description="域名为【{}】的租户已存在",
        message_key="system.tenant.website_duplicate",
    )
    TENANT_ROLE_NOT_MATCH = ErrorCode(
        code=1_002_015_006,
        description="角色({})的租户({})不匹配",
        message_key="system.tenant.role_not_match",
    )

    # ========== 租户套餐 1-002-016-000 ==========
    TENANT_PACKAGE_NOT_EXISTS = ErrorCode(
        code=1_002_016_000,
        description="租户套餐不存在",
        message_key="system.tenant_package.not_exists",
    )
    TENANT_PACKAGE_USED = ErrorCode(
        code=1_002_016_001,
        description="租户正在使用该套餐，请给租户重新设置套餐后再尝试删除",
        message_key="system.tenant_package.used",
    )
    TENANT_PACKAGE_DISABLE = ErrorCode(
        code=1_002_016_002,
        description="名字为【{}】的租户套餐已被禁用",
        message_key="system.tenant_package.disable",
    )
    TENANT_PACKAGE_NAME_DUPLICATE = ErrorCode(
        code=1_002_016_003,
        description="已经存在该名字的租户套餐",
        message_key="system.tenant_package.name_duplicate",
    )

    # ========== OAuth2 客户端 1-002-020-000 ==========
    OAUTH2_CLIENT_NOT_EXISTS = ErrorCode(
        code=1_002_020_000,
        description="OAuth2 客户端不存在",
        message_key="system.oauth2_client.not_exists",
    )
    OAUTH2_CLIENT_EXISTS = ErrorCode(
        code=1_002_020_001,
        description="OAuth2 客户端编号已存在",
        message_key="system.oauth2_client.exists",
    )
    OAUTH2_CLIENT_DISABLE = ErrorCode(
        code=1_002_020_002,
        description="OAuth2 客户端已禁用",
        message_key="system.oauth2_client.disable",
    )
    OAUTH2_CLIENT_AUTHORIZED_GRANT_TYPE_NOT_EXISTS = ErrorCode(
        code=1_002_020_003,
        description="不支持该授权类型",
        message_key="system.oauth2_client.grant_type_not_exists",
    )
    OAUTH2_CLIENT_SCOPE_OVER = ErrorCode(
        code=1_002_020_004,
        description="授权范围过大",
        message_key="system.oauth2_client.scope_over",
    )
    OAUTH2_CLIENT_REDIRECT_URI_NOT_MATCH = ErrorCode(
        code=1_002_020_005,
        description="无效 redirect_uri: {}",
        message_key="system.oauth2_client.redirect_uri_not_match",
    )
    OAUTH2_CLIENT_CLIENT_SECRET_ERROR = ErrorCode(
        code=1_002_020_006,
        description="无效 client_secret: {}",
        message_key="system.oauth2_client.client_secret_error",
    )

    # ========== OAuth2 授权 1-002-021-000 ==========
    OAUTH2_GRANT_CLIENT_ID_MISMATCH = ErrorCode(
        code=1_002_021_000,
        description="client_id 不匹配",
        message_key="system.oauth2_grant.client_id_mismatch",
    )
    OAUTH2_GRANT_REDIRECT_URI_MISMATCH = ErrorCode(
        code=1_002_021_001,
        description="redirect_uri 不匹配",
        message_key="system.oauth2_grant.redirect_uri_mismatch",
    )
    OAUTH2_GRANT_STATE_MISMATCH = ErrorCode(
        code=1_002_021_002,
        description="state 不匹配",
        message_key="system.oauth2_grant.state_mismatch",
    )
    OAUTH2_GRANT_CLIENT_USER_TYPE_MISMATCH = ErrorCode(
        code=1_002_021_003,
        description="客户端不支持该用户类型授权",
        message_key="system.oauth2_grant.client_user_type_mismatch",
    )
    OAUTH2_GRANT_CLIENT_NOT_CLIENT_TYPE = ErrorCode(
        code=1_002_021_004,
        description="该客户端不允许使用客户端凭证模式",
        message_key="system.oauth2_grant.not_client_type",
    )

    # ========== OAuth2 授权码 1-002-022-000 ==========
    OAUTH2_CODE_NOT_EXISTS = ErrorCode(
        code=1_002_022_000, description="code 不存在", message_key="system.oauth2_code.not_exists"
    )
    OAUTH2_CODE_EXPIRE = ErrorCode(
        code=1_002_022_001, description="code 已过期", message_key="system.oauth2_code.expire"
    )

    # ========== 邮箱账号 1-002-023-000 ==========
    MAIL_ACCOUNT_NOT_EXISTS = ErrorCode(
        code=1_002_023_000,
        description="邮箱账号不存在",
        message_key="system.mail_account.not_exists",
    )
    MAIL_ACCOUNT_RELATE_TEMPLATE_EXISTS = ErrorCode(
        code=1_002_023_001,
        description="无法删除，该邮箱账号还有邮件模板",
        message_key="system.mail_account.relate_template_exists",
    )

    # ========== 邮件模版 1-002-024-000 ==========
    MAIL_TEMPLATE_NOT_EXISTS = ErrorCode(
        code=1_002_024_000,
        description="邮件模版不存在",
        message_key="system.mail_template.not_exists",
    )
    MAIL_TEMPLATE_CODE_EXISTS = ErrorCode(
        code=1_002_024_001,
        description="邮件模版 code({}) 已存在",
        message_key="system.mail_template.code_exists",
    )

    # ========== 邮件发送 1-002-025-000 ==========
    MAIL_SEND_TEMPLATE_PARAM_MISS = ErrorCode(
        code=1_002_025_000,
        description="模板参数({})缺失",
        message_key="system.mail_send.template_param_miss",
    )
    MAIL_SEND_MAIL_NOT_EXISTS = ErrorCode(
        code=1_002_025_001, description="邮箱不存在", message_key="system.mail_send.mail_not_exists"
    )

    # ========== 站内信模版 1-002-026-000 ==========
    NOTICE_TEMPLATE_NOT_EXISTS = ErrorCode(
        code=1_002_026_000,
        description="站内信模版不存在",
        message_key="system.notice_template.not_exists",
    )
    NOTICE_TEMPLATE_CODE_DUPLICATE = ErrorCode(
        code=1_002_026_001,
        description="已经存在编码为【{}】的站内信模板",
        message_key="system.notice_template.code_duplicate",
    )

    # ========== 站内信发送 1-002-028-000 ==========
    NOTICE_SEND_TEMPLATE_PARAM_MISS = ErrorCode(
        code=1_002_028_000,
        description="模板参数({})缺失",
        message_key="system.notice_send.template_param_miss",
    )
    NOTICE_SEND_BATCH_PARAM_MISMATCH = ErrorCode(
        code=1_002_028_001,
        description="批量发送参数不匹配，用户数量({})与参数列表数量({})不一致",
        message_key="system.notice_send.batch_param_mismatch",
    )
    NOTICE_SEND_USER_NOT_EXISTS = ErrorCode(
        code=1_002_028_002,
        description="发送失败，用户不存在",
        message_key="system.notice_send.user_not_exists",
    )
    NOTICE_SEND_TEMPLATE_DISABLED = ErrorCode(
        code=1_002_028_003,
        description="发送失败，站内信模板已禁用",
        message_key="system.notice_send.template_disabled",
    )

    # ========== SDK 模块 1-002-029-000 ==========
    SDK_CHANNEL_NOT_FOUND = ErrorCode(
        code=1_002_029_000, description="SDK渠道不存在", message_key="system.sdk.channel_not_found"
    )

    # ========== 验证码模块 1-002-030-000 ==========
    CAPTCHA_TYPE_INVALID = ErrorCode(
        code=1_002_030_001,
        description="无效的验证码类型【{}】",
        message_key="system.captcha.type_invalid",
    )
    CAPTCHA_NOT_FOUND_OR_EXPIRED = ErrorCode(
        code=1_002_030_002,
        description="验证码已过期",
        message_key="system.captcha.not_found_or_expired",
    )
    CAPTCHA_VERIFICATION_FAILED = ErrorCode(
        code=1_002_030_003,
        description="验证码验证失败",
        message_key="system.captcha.verification_failed",
    )
    CAPTCHA_SERVICE_UNAVAILABLE = ErrorCode(
        code=1_002_030_004,
        description="验证码服务暂时不可用",
        message_key="system.captcha.service_unavailable",
    )
    CAPTCHA_VERIFICATION_FREQUENT = ErrorCode(
        code=1_002_030_005,
        description="请求过于频繁，请{}秒后重试",
        message_key="system.captcha.verification_frequent",
    )
    CAPTCHA_FAILED_TOO_MANY_ATTEMPTS = ErrorCode(
        code=1_002_030_006,
        description="错误尝试次数过多，账户被锁定，请{}秒后重试",
        message_key="system.captcha.failed_too_many_attempts",
    )
    CAPTCHA_VERIFICATION_PARAM_MISS = ErrorCode(
        code=1_002_030_007,
        description="缺少必要的验证码参数",
        message_key="system.captcha.verification_param_miss",
    )

    # ========== IP 地区 1-002-031-000 ==========
    IP_AREA_NOT_FOUND = ErrorCode(
        code=1_002_031_000, description="IP 地区信息未找到", message_key="system.ip_area.not_found"
    )

    # ========== 社交客户端 1-002-032-000 ==========
    SOCIAL_CLIENT_NOT_EXISTS = ErrorCode(
        code=1_002_032_000,
        description="社交客户端配置不存在",
        message_key="system.social.client_not_exists",
    )
    SOCIAL_CLIENT_NOT_SUPPORTED = ErrorCode(
        code=1_002_032_001,
        description="不支持的社交类型：{}",
        message_key="system.social.client_not_supported",
    )
    SOCIAL_CLIENT_UNIQUE = ErrorCode(
        code=1_002_032_002,
        description="社交客户端配置已存在：{}",
        message_key="system.social.client_unique",
    )
    SOCIAL_CLIENT_AUTH_FAILURE = ErrorCode(
        code=1_002_032_003,
        description="社交客户端认证失败：{}",
        message_key="system.social.client_auth_failure",
    )
    SOCIAL_USER_AUTH_FAILURE = ErrorCode(
        code=1_002_032_004,
        description="社交用户认证失败：{}",
        message_key="system.social.user_auth_failure",
    )
    SOCIAL_USER_NOT_FOUND = ErrorCode(
        code=1_002_032_005, description="社交用户不存在", message_key="system.social.user_not_found"
    )
    SOCIAL_WECHAT_MP_JS_SDK_SIGNATURE_ERROR = ErrorCode(
        code=1_002_032_006,
        description="微信公众号 JSAPI 签名失败：{}",
        message_key="system.social.wechat_mp_js_sdk_signature_error",
    )
    SOCIAL_CLIENT_WEIXIN_MINI_APP_PHONE_CODE_ERROR = ErrorCode(
        code=1_002_032_007,
        description="微信小程序获取手机号失败：{}",
        message_key="system.social.weixin_mini_app_phone_code_error",
    )
    SOCIAL_CLIENT_WEIXIN_MINI_APP_QRCODE_ERROR = ErrorCode(
        code=1_002_032_008,
        description="微信小程序获取二维码失败：{}",
        message_key="system.social.weixin_mini_app_qrcode_error",
    )
    SOCIAL_CLIENT_WEIXIN_MINI_APP_SUBSCRIBE_TEMPLATE_ERROR = ErrorCode(
        code=1_002_032_009,
        description="微信小程序获取订阅模板失败：{}",
        message_key="system.social.weixin_mini_app_subscribe_template_error",
    )
    SOCIAL_CLIENT_WEIXIN_MINI_APP_SUBSCRIBE_MESSAGE_ERROR = ErrorCode(
        code=1_002_032_010,
        description="微信小程序发送订阅消息失败：{}",
        message_key="system.social.weixin_mini_app_subscribe_message_error",
    )
    SOCIAL_PLATFORM_NOT_EXIST = ErrorCode(
        code=1_002_032_011,
        description="社交平台【{}】不存在",
        message_key="system.social.platform_not_exist",
    )
    SOCIAL_CLIENT_WEIXIN_MINI_APP_ORDER_SHIPPING_ERROR = ErrorCode(
        code=1_002_032_012,
        description="微信小程序订单发货同步失败：{}",
        message_key="system.social.weixin_mini_app_order_shipping_error",
    )
    SOCIAL_CLIENT_WEIXIN_MINI_APP_ORDER_CONFIRM_RECEIVE_ERROR = ErrorCode(
        code=1_002_032_013,
        description="微信小程序订单确认收货同步失败：{}",
        message_key="system.social.weixin_mini_app_order_confirm_receive_error",
    )
