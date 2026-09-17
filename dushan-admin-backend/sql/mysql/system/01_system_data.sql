-- 由 simple 业务初始数据适配 Native；默认账号密码 admin123，bcrypt cost=12。

SET NAMES utf8mb4;

SET time_zone = '+00:00';

INSERT IGNORE INTO `system_tenant_package` (`id`, `name`, `status`, `remark`, `menu_ids`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10100000090001, '标准套餐', 1, '包含系统管理与基础设施全部功能', '[]', 'system', NOW(), 'system', NOW(), b'0');

INSERT IGNORE INTO `system_tenant` (`id`, `name`, `contact_user_id`, `contact_name`, `contact_mobile`, `status`, `websites`, `package_id`, `expire_time`, `account_count`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(1, '渡山无界', 10100000010001, '管理员', '19053131342', 1, '["http://localhost"]', 10100000090001, '2099-12-31 23:59:59', 9999, 'system', NOW(), 'system', NOW(), b'0');

INSERT IGNORE INTO `system_dept` (`id`, `name`, `parent_id`, `sort`, `leader_user_id`, `phone`, `email`, `status`, `tenant_id`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10100000020001, '渡山无界', 0, 1, 10100000010001, '19053131342', '729227973@qq.com', 1, '1', 'system', NOW(), 'system', NOW(), b'0'),
(10100000020002, '技术部', 10100000020001, 1, NULL, NULL, NULL, 1, '1', 'system', NOW(), 'system', NOW(), b'0'),
(10100000020003, '产品部', 10100000020001, 2, NULL, NULL, NULL, 1, '1', 'system', NOW(), 'system', NOW(), b'0'),
(10100000020004, '运营部', 10100000020001, 3, NULL, NULL, NULL, 1, '1', 'system', NOW(), 'system', NOW(), b'0');

INSERT IGNORE INTO `system_post` (`id`, `code`, `name`, `sort`, `status`, `remark`, `tenant_id`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10100000030001, 'CEO', '董事长', 1, 1, NULL, '1', 'system', NOW(), 'system', NOW(), b'0'),
(10100000030002, 'CTO', '技术总监', 2, 1, NULL, '1', 'system', NOW(), 'system', NOW(), b'0'),
(10100000030003, 'PM', '项目经理', 3, 1, NULL, '1', 'system', NOW(), 'system', NOW(), b'0'),
(10100000030004, 'DEV', '开发工程师', 4, 1, NULL, '1', 'system', NOW(), 'system', NOW(), b'0'),
(10100000030005, 'OPS', '运维工程师', 5, 1, NULL, '1', 'system', NOW(), 'system', NOW(), b'0');

INSERT IGNORE INTO `system_role` (`id`, `name`, `code`, `sort`, `data_scope`, `data_scope_dept_ids`, `builtin`, `status`, `remark`, `tenant_id`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10100000040001, '超级管理员', 'super_admin', 1, 1, '[]', 1, 1, '超级管理员，拥有所有权限', '1', 'system', NOW(), 'system', NOW(), b'0'),
(10100000040002, '普通角色', 'common', 2, 1, '[]', 1, 1, '普通角色，基础操作权限', '1', 'system', NOW(), 'system', NOW(), b'0'),
(10100000040003, '只读角色', 'readonly', 3, 1, '[]', 2, 1, '只读角色，仅查看权限', '1', 'system', NOW(), 'system', NOW(), b'0');

INSERT IGNORE INTO `system_users` (`id`, `username`, `password`, `nickname`, `remark`, `dept_id`, `post_ids`, `email`, `mobile`, `sex`, `avatar`, `status`, `login_ip`, `login_date`, `tenant_id`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `credential_revision`, `authorization_revision`) VALUES
(10100000010001, 'admin', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '管理员', '超级管理员', 10100000020001, '[10100000030001]', '729227973@qq.com', '19053131342', 0, '', 1, '127.0.0.1', NOW(), '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010002, 'dushan', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '渡山', '技术总监', 10100000020002, '[10100000030002]', 'dushan@dushan.com', '13800138001', 1, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010003, 'zhangsan', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '张三', '项目经理', 10100000020002, '[10100000030003]', 'zhangsan@dushan.com', '13800138002', 1, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1);

INSERT IGNORE INTO `system_user_profiles` (`id`, `user_id`, `bio`, `tags`, `address`, `skills`, `work_scope`, `expertise`, `communication_style`, `ai_preference`, `tenant_id`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10100000050001, 10100000010001, '系统超级管理员', '["管理员", "全栈"]', '渡山无界总部', '["Python", "FastAPI", "Vue3"]', '系统架构设计与全局管理', '全栈开发、系统架构', 'technical', '{"response_style": "detailed", "preferred_format": "table", "language": "zh-CN", "tone": "professional", "auto_summary": true}', '1', 'system', NOW(), 'system', NOW(), b'0'),
(10100000050002, 10100000010002, '技术总监，负责架构设计', '["CTO", "架构师"]', '渡山无界总部', '["Python", "Go", "微服务", "K8s"]', '技术架构设计与团队管理', '微服务架构、云原生', 'technical', '{"response_style": "concise", "preferred_format": "list", "language": "zh-CN", "tone": "professional", "auto_summary": false}', '1', 'system', NOW(), 'system', NOW(), b'0'),
(10100000050003, 10100000010003, '项目经理，负责项目交付', '["PM", "敏捷"]', '渡山无界总部', '["项目管理", "Scrum", "JIRA"]', '项目交付与团队协调', '敏捷项目管理', 'formal', '{"response_style": "balanced", "preferred_format": "paragraph", "language": "zh-CN", "tone": "friendly", "auto_summary": true}', '1', 'system', NOW(), 'system', NOW(), b'0');

INSERT IGNORE INTO `system_user_post` (`id`, `user_id`, `post_id`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `tenant_id`) VALUES
(10100000060001, 10100000010001, 10100000030001, 'system', NOW(), 'system', NOW(), b'0', '1'),
(10100000060002, 10100000010002, 10100000030002, 'system', NOW(), 'system', NOW(), b'0', '1'),
(10100000060003, 10100000010003, 10100000030003, 'system', NOW(), 'system', NOW(), b'0', '1');

INSERT IGNORE INTO `system_user_role` (`id`, `user_id`, `role_id`, `tenant_id`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10100000070001, 10100000010001, 10100000040001, '1', 'system', NOW(), 'system', NOW(), b'0'),
(10100000070002, 10100000010002, 10100000040002, '1', 'system', NOW(), 'system', NOW(), b'0'),
(10100000070003, 10100000010003, 10100000040002, '1', 'system', NOW(), 'system', NOW(), b'0');

INSERT IGNORE INTO `system_oauth2_client` (`id`, `client_id`, `secret`, `name`, `logo`, `description`, `status`, `user_type`, `access_token_validity_seconds`, `refresh_token_validity_seconds`, `redirect_uris`, `authorized_grant_types`, `scopes`, `auto_approve_scopes`, `authorities`, `resource_ids`, `additional_information`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `credential_revision`) VALUES
(10100000080001, 'default', 'dushan-admin-secret', '渡山管理后台', '', '默认管理后台客户端', 1, 2, 1800, 2592000, '["http://localhost"]', '["password", "authorization_code", "refresh_token", "implicit"]', '["user.read", "user.write"]', '["user.read"]', '[]', '[]', NULL, 'system', NOW(), 'system', NOW(), b'0', 1);

INSERT IGNORE INTO `system_notification_notice` (`id`, `code`, `title`, `content`, `type`, `user_type`, `channels`, `sms_template_code`, `mail_account_id`, `publisher`, `status`, `tenant_id`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10100000100001, 'system_announcement_publish', '公告', '<p>这是一个公告。</p>', 1, 2, '["INTERNAL"]', 'system-notice', 10100000085001, '渡山', 1, '1', '10100000010001', '2026-02-14 10:56:36', '10100000010001', '2026-02-14 12:48:24', b'0');

INSERT IGNORE INTO system_authorization_revision (id, revision, creator, updater, create_time, update_time, deleted) VALUES (1, 1, '', '', UTC_TIMESTAMP(), UTC_TIMESTAMP(), 0);
