class WorkloadConstants:
    """服务器登记的任务及最小租户资源集合，不接收客户端授权声明。"""

    CAPABILITIES = {
        "mq.outbox.dispatch": {
            "source": "mq.outbox",
            "additional_sources": (),
            "resources": {"infra_mq_outbox": frozenset({"delete", "select", "update"})},
        },
        "system.auth.revoke": {
            "source": "system.auth",
            "additional_sources": (),
            "resources": {
                "system_users": frozenset({"select"}),
                "system_login_log": frozenset({"insert", "select"}),
                "system_oauth2_access_token": frozenset({"select", "update"}),
                "system_oauth2_refresh_token": frozenset({"select", "update"}),
            },
        },
        "infra.database.backup": {
            "source": "module_infra",
            "additional_sources": (),
            "resources": {},
        },
        "infra.database.observe": {
            "source": "module_infra",
            "additional_sources": (),
            "resources": {},
        },
        "infra.log.access.clean": {
            "source": "module_infra",
            "additional_sources": (),
            "resources": {"infra_api_access_log": frozenset({"delete", "select"})},
        },
        "infra.log.error.clean": {
            "source": "module_infra",
            "additional_sources": (),
            "resources": {"infra_api_error_log": frozenset({"delete", "select"})},
        },
        "infra.job.log.clean": {
            "source": "module_infra",
            "additional_sources": (),
            "resources": {},
        },
        "infra.log.write": {
            "source": "module_infra",
            "additional_sources": (),
            "resources": {
                "infra_api_access_log": frozenset({"insert"}),
                "infra_api_error_log": frozenset({"insert"}),
            },
        },
        "infra.config.sync": {
            "source": "module_infra",
            "additional_sources": (),
            "resources": {
                "infra_config_data": frozenset({"select"}),
                "infra_config_type": frozenset({"select"}),
            },
        },
        "infra.file.read": {
            "source": "module_infra",
            "additional_sources": (),
            "resources": {
                "infra_file_config": frozenset({"select"}),
                "infra_file": frozenset({"select"}),
                "infra_file_content": frozenset({"select"}),
            },
        },
        "system.auth": {
            "source": "system.auth",
            "additional_sources": (),
            "resources": {
                "system_users": frozenset({"insert", "select", "update"}),
                "system_login_log": frozenset({"insert", "select"}),
                "system_oauth2_access_token": frozenset({"insert", "select", "update"}),
                "system_oauth2_refresh_token": frozenset({"insert", "select", "update"}),
                "system_oauth2_code": frozenset({"insert", "select", "update"}),
                "system_oauth2_approve": frozenset({"delete", "insert", "select", "update"}),
                "system_social_client": frozenset({"select"}),
                "system_social_user": frozenset({"insert", "select", "update"}),
                "system_social_user_bind": frozenset({"delete", "insert", "select", "update"}),
                "system_user_post": frozenset({"insert", "delete", "select"}),
                "system_role": frozenset({"select"}),
                "system_user_role": frozenset({"select"}),
                "system_dept": frozenset({"select"}),
                "system_post": frozenset({"select"}),
                "system_sms_code": frozenset({"insert", "select", "update"}),
                "system_sms_channel": frozenset({"select"}),
                "system_sms_template": frozenset({"select"}),
                "system_sms_log": frozenset({"insert", "select", "update"}),
                "system_mail_log": frozenset({"insert", "select", "update"}),
            },
        },
        "system.tenant.provision": {
            "source": "system.tenant",
            "additional_sources": (),
            "resources": {
                "system_users": frozenset({"insert", "select", "update"}),
                "system_role": frozenset({"insert", "select", "update"}),
                "system_user_role": frozenset({"delete", "insert", "select", "update"}),
                "system_role_menu": frozenset({"delete", "insert", "select", "update"}),
            },
        },
        "system.announcement.publish": {
            "source": "module_system",
            "additional_sources": (),
            "resources": {
                "system_announcement": frozenset({"select", "update"}),
                "system_notification_notice": frozenset({"insert", "select", "update"}),
                "system_notification_notice_log": frozenset({"insert", "select", "update"}),
                "system_notification_message": frozenset({"insert", "select", "update"}),
                "system_users": frozenset({"select"}),
                "system_dept": frozenset({"select"}),
            },
        },
        "system.permission.sync": {
            "source": "module_system",
            "additional_sources": (),
            "resources": {},
        },
        "system.mail.send": {
            "source": "module_system",
            "additional_sources": ("system.auth",),
            "resources": {"system_mail_log": frozenset({"select", "update"})},
        },
        "system.sms.send": {
            "source": "module_system",
            "additional_sources": ("system.auth",),
            "resources": {
                "system_sms_channel": frozenset({"select"}),
                "system_sms_log": frozenset({"select", "update"}),
            },
        },
    }
    PROTECTED = frozenset(
        {
            "infra_api_access_log",
            "infra_api_error_log",
            "system_login_log",
            "system_notification_message",
            "system_operate_log",
            "system_user_post",
            "system_users",
        }
    )
