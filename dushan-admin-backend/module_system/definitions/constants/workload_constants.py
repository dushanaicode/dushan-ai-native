class WorkloadConstants:
    """服务器登记的任务及最小租户资源集合，不接收客户端授权声明。"""

    SOURCES = {
        "module_infra": frozenset(
            {
                "infra.log.access.clean",
                "infra.log.error.clean",
                "infra.job.log.clean",
                "infra.log.write",
                "infra.config.sync",
                "infra.file.read",
                "infra.database.backup",
                "infra.database.observe",
            }
        ),
        "system.auth": frozenset({"system.auth", "system.sms.send", "system.mail.send"}),
        "module_system": frozenset(
            {
                "system.announcement.publish",
                "system.permission.sync",
                "system.sms.send",
                "system.mail.send",
            }
        ),
        "system.tenant": frozenset({"system.tenant.provision"}),
    }
    SOURCE_BY_CAPABILITY = {
        **dict.fromkeys(
            (
                "infra.log.access.clean",
                "infra.log.error.clean",
                "infra.job.log.clean",
                "infra.log.write",
                "infra.config.sync",
                "infra.file.read",
                "infra.database.backup",
                "infra.database.observe",
            ),
            "module_infra",
        ),
        "system.auth": "system.auth",
        "system.tenant.provision": "system.tenant",
        "system.announcement.publish": "module_system",
        "system.permission.sync": "module_system",
        "system.mail.send": "module_system",
        "system.sms.send": "module_system",
    }
    RESOURCES = {
        "infra.database.backup": {},
        "infra.database.observe": {},
        "infra.log.access.clean": {"infra_api_access_log": frozenset({"select", "delete"})},
        "infra.log.error.clean": {"infra_api_error_log": frozenset({"select", "delete"})},
        "infra.job.log.clean": {},
        "infra.log.write": {
            "infra_api_access_log": frozenset({"insert"}),
            "infra_api_error_log": frozenset({"insert"}),
        },
        "infra.config.sync": {
            "infra_config_data": frozenset({"select"}),
            "infra_config_type": frozenset({"select"}),
        },
        "infra.file.read": {
            "infra_file_config": frozenset({"select"}),
            "infra_file": frozenset({"select"}),
            "infra_file_content": frozenset({"select"}),
        },
        "system.auth": {
            "system_users": frozenset({"select", "insert", "update"}),
            "system_login_log": frozenset({"select", "insert"}),
            "system_oauth2_access_token": frozenset({"select", "insert", "update"}),
            "system_oauth2_refresh_token": frozenset({"select", "insert", "update"}),
            "system_oauth2_code": frozenset({"select", "insert", "update"}),
            "system_oauth2_approve": frozenset({"select", "insert", "update", "delete"}),
            "system_social_client": frozenset({"select"}),
            "system_social_user": frozenset({"select", "insert", "update"}),
            "system_social_user_bind": frozenset({"select", "insert", "update", "delete"}),
            "system_user_post": frozenset({"select", "insert", "delete"}),
            "system_role": frozenset({"select"}),
            "system_user_role": frozenset({"select"}),
            "system_dept": frozenset({"select"}),
            "system_post": frozenset({"select"}),
            "system_sms_code": frozenset({"select", "insert", "update"}),
            "system_sms_channel": frozenset({"select"}),
            "system_sms_log": frozenset({"select", "insert", "update"}),
            "system_mail_log": frozenset({"select", "insert", "update"}),
        },
        "system.tenant.provision": {
            "system_users": frozenset({"select", "insert", "update"}),
            "system_role": frozenset({"select", "insert", "update"}),
            "system_user_role": frozenset({"select", "insert", "update", "delete"}),
            "system_role_menu": frozenset({"select", "insert", "update", "delete"}),
        },
        "system.announcement.publish": {
            "system_announcement": frozenset({"select", "update"}),
            "system_notification_notice": frozenset({"select", "insert", "update"}),
            "system_notification_notice_log": frozenset({"select", "insert", "update"}),
            "system_notification_message": frozenset({"select", "insert", "update"}),
            "system_users": frozenset({"select"}),
            "system_dept": frozenset({"select"}),
        },
        "system.permission.sync": {},
        "system.mail.send": {"system_mail_log": frozenset({"select", "update"})},
        "system.sms.send": {
            "system_sms_channel": frozenset({"select"}),
            "system_sms_log": frozenset({"select", "update"}),
        },
    }
    PROTECTED = frozenset(
        {
            "infra_api_access_log",
            "infra_api_error_log",
            "system_users",
            "system_login_log",
            "system_operate_log",
            "system_user_post",
            "system_notification_message",
        }
    )
