from fastapi import APIRouter

from module_system.controller.admin.announcement.announcement_controller import (
    announcement_controller,
)
from module_system.controller.admin.area.area_controller import area_controller
from module_system.controller.admin.auth.auth_controller import auth_controller
from module_system.controller.admin.captcha.captcha_controller import captcha_controller
from module_system.controller.admin.dept.dept_controller import dept_controller
from module_system.controller.admin.dept.post_controller import post_controller
from module_system.controller.admin.dict.dict_data_controller import dict_data_controller
from module_system.controller.admin.dict.dict_type_controller import dict_type_controller
from module_system.controller.admin.logger.login_log_controller import login_log_controller
from module_system.controller.admin.logger.operate_log_controller import (
    operate_log_controller,
)
from module_system.controller.admin.mail.mail_account_controller import mail_account_controller
from module_system.controller.admin.mail.mail_log_controller import mail_log_controller
from module_system.controller.admin.mail.mail_template_controller import mail_template_controller
from module_system.controller.admin.notification.notice_controller import (
    notice_controller,
)
from module_system.controller.admin.notification.notice_log_controller import (
    notice_log_controller,
)
from module_system.controller.admin.notification.notice_message_controller import (
    notice_message_controller,
)
from module_system.controller.admin.oauth2.oauth2_client_controller import oauth2_client_controller
from module_system.controller.admin.oauth2.oauth2_open_controller import oauth2_open_controller
from module_system.controller.admin.oauth2.oauth2_token_controller import oauth2_token_controller
from module_system.controller.admin.oauth2.oauth2_user_controller import oauth2_user_controller
from module_system.controller.admin.permission.menu_controller import menu_controller
from module_system.controller.admin.permission.permission_controller import permission_controller
from module_system.controller.admin.permission.role_controller import role_controller
from module_system.controller.admin.sms.sms_callback_controller import sms_callback_controller
from module_system.controller.admin.sms.sms_channel_controller import sms_channel_controller
from module_system.controller.admin.sms.sms_log_controller import sms_log_controller
from module_system.controller.admin.sms.sms_template_controller import sms_template_controller
from module_system.controller.admin.social.social_client_controller import social_client_controller
from module_system.controller.admin.social.social_user_controller import social_user_controller
from module_system.controller.admin.tenant.tenant_controller import tenant_controller
from module_system.controller.admin.tenant.tenant_package_controller import (
    tenant_package_controller,
)
from module_system.controller.admin.user.user_controller import user_controller
from module_system.controller.admin.user.user_profile_controller import user_profile_controller

# 创建Admin端二级路由器
admin_router = APIRouter()

# 包含三级路由（控制器）
admin_router.include_router(area_controller, tags=["System - 地区管理"])
admin_router.include_router(auth_controller, tags=["System - 认证管理"])
admin_router.include_router(captcha_controller, tags=["System - 验证码管理"])
admin_router.include_router(dept_controller, tags=["System - 部门管理"])
admin_router.include_router(post_controller, tags=["System - 岗位管理"])
admin_router.include_router(dict_type_controller, tags=["System - 字典类型管理"])
admin_router.include_router(dict_data_controller, tags=["System - 字典数据管理"])
admin_router.include_router(login_log_controller, tags=["System - 登录日志管理"])
admin_router.include_router(mail_account_controller, tags=["System - 邮件账户管理"])
admin_router.include_router(mail_log_controller, tags=["System - 邮件日志管理"])
admin_router.include_router(mail_template_controller, tags=["System - 邮件模板管理"])
admin_router.include_router(menu_controller, tags=["System - 菜单管理"])
admin_router.include_router(notice_controller, tags=["System - 通知管理"])
admin_router.include_router(announcement_controller, tags=["System - 公告管理"])
admin_router.include_router(notice_message_controller, tags=["System - 通知消息管理"])
admin_router.include_router(notice_log_controller, tags=["System - 通知日志管理"])
admin_router.include_router(oauth2_client_controller, tags=["System - OAuth2 客户端管理"])
admin_router.include_router(oauth2_token_controller, tags=["System - OAuth2 令牌管理"])
admin_router.include_router(oauth2_open_controller, tags=["System - OAuth2 授权管理"])
admin_router.include_router(oauth2_user_controller, tags=["System - OAuth2 用户管理"])
admin_router.include_router(operate_log_controller, tags=["System - 操作日志管理"])
admin_router.include_router(permission_controller, tags=["System - 权限管理"])
admin_router.include_router(role_controller, tags=["System - 角色管理"])
admin_router.include_router(sms_callback_controller, tags=["System - 短信回调管理"])
admin_router.include_router(sms_channel_controller, tags=["System - 短信渠道管理"])
admin_router.include_router(sms_log_controller, tags=["System - 短信日志管理"])
admin_router.include_router(sms_template_controller, tags=["System - 短信模板管理"])
admin_router.include_router(social_client_controller, tags=["System - 社交客户端管理"])
admin_router.include_router(social_user_controller, tags=["System - 社交用户管理"])
admin_router.include_router(tenant_controller, tags=["System - 租户管理"])
admin_router.include_router(tenant_package_controller, tags=["System - 租户套餐管理"])
admin_router.include_router(user_controller, tags=["System - 用户管理"])
admin_router.include_router(user_profile_controller, tags=["System - 用户个人中心"])
