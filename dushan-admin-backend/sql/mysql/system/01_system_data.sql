-- 由 simple 业务初始数据适配 Native；默认账号密码 admin123，bcrypt cost=12。

SET NAMES utf8mb4;

SET time_zone = '+00:00';

INSERT IGNORE INTO `system_tenant_package` (`id`, `name`, `status`, `remark`, `menu_ids`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10100000090001, '标准套餐', 1, '包含系统管理与基础设施全部功能', '[]', 'system', NOW(), 'system', NOW(), b'0');

INSERT IGNORE INTO `system_tenant` (`id`, `name`, `contact_user_id`, `contact_name`, `contact_mobile`, `status`, `websites`, `package_id`, `expire_time`, `account_count`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(1, '渡山科技', 10100000010001, '管理员', '19053131342', 1, '["http://localhost"]', 10100000090001, '2099-12-31 23:59:59', 9999, 'system', NOW(), 'system', NOW(), b'0');

INSERT IGNORE INTO `system_dept` (`id`, `name`, `parent_id`, `sort`, `leader_user_id`, `phone`, `email`, `status`, `tenant_id`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10100000020001, '渡山科技', 0, 1, 10100000010001, '19053131342', '729227973@qq.com', 1, '1', 'system', NOW(), 'system', NOW(), b'0'),
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
(10100000010003, 'zhangsan', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '张三', '项目经理', 10100000020002, '[10100000030003]', 'zhangsan@dushan.com', '13800138002', 1, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010004, 'lisi', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '李四', '开发工程师', 10100000020003, '[10100000030004]', 'lisi@dushan.com', '13800138003', 0, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010005, 'wangwu', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '王五', '运维工程师', 10100000020004, '[10100000030005]', 'wangwu@dushan.com', '13800138004', 1, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010006, 'user06', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '赵六', '测试工程师', 10100000020002, '[]', 'user06@dushan.com', '13800138006', 0, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010007, 'user07', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '孙七', '前端开发', 10100000020002, '[]', 'user07@dushan.com', '13800138007', 1, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010008, 'user08', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '周八', '后端开发', 10100000020002, '[]', 'user08@dushan.com', '13800138008', 0, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010009, 'user09', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '吴九', 'UI设计师', 10100000020003, '[]', 'user09@dushan.com', '13800138009', 1, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010010, 'user10', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '郑十', '产品经理', 10100000020003, '[]', 'user10@dushan.com', '13800138010', 0, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010011, 'user11', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '陈十一', 'DBA', 10100000020002, '[]', 'user11@dushan.com', '13800138011', 1, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010012, 'user12', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '林十二', '安全工程师', 10100000020002, '[]', 'user12@dushan.com', '13800138012', 0, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010013, 'user13', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '黄十三', '测试主管', 10100000020003, '[]', 'user13@dushan.com', '13800138013', 1, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010014, 'user14', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '杨十四', '运营专员', 10100000020004, '[]', 'user14@dushan.com', '13800138014', 0, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010015, 'user15', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '何十五', '数据分析师', 10100000020004, '[]', 'user15@dushan.com', '13800138015', 1, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010016, 'user16', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '罗十六', '架构师', 10100000020002, '[]', 'user16@dushan.com', '13800138016', 0, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010017, 'user17', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '马十七', '客服主管', 10100000020004, '[]', 'user17@dushan.com', '13800138017', 1, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010018, 'user18', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '宋十八', 'DevOps工程师', 10100000020002, '[]', 'user18@dushan.com', '13800138018', 0, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010019, 'user19', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '谢十九', 'SRE工程师', 10100000020002, '[]', 'user19@dushan.com', '13800138019', 1, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010020, 'user20', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '韩二十', '算法工程师', 10100000020003, '[]', 'user20@dushan.com', '13800138020', 0, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010021, 'user21', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '唐二一', '移动开发', 10100000020002, '[]', 'user21@dushan.com', '13800138021', 1, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010022, 'user22', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '冯二二', '技术支持', 10100000020004, '[]', 'user22@dushan.com', '13800138022', 0, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010023, 'user23', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '曹二三', 'QA工程师', 10100000020003, '[]', 'user23@dushan.com', '13800138023', 1, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010024, 'user24', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '袁二四', '内容运营', 10100000020004, '[]', 'user24@dushan.com', '13800138024', 0, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1),
(10100000010025, 'user25', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '许二五', '人事专员', 10100000020001, '[]', 'user25@dushan.com', '13800138025', 1, '', 1, '', NULL, '1', 'system', NOW(), 'system', NOW(), b'0', 1, 1);

INSERT IGNORE INTO `system_user_profiles` (`id`, `user_id`, `bio`, `tags`, `address`, `skills`, `work_scope`, `expertise`, `communication_style`, `ai_preference`, `tenant_id`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10100000050001, 10100000010001, '系统超级管理员', '["管理员", "全栈"]', '渡山科技总部', '["Python", "FastAPI", "Vue3"]', '系统架构设计与全局管理', '全栈开发、系统架构', 'technical', '{"response_style": "detailed", "preferred_format": "table", "language": "zh-CN", "tone": "professional", "auto_summary": true}', '1', 'system', NOW(), 'system', NOW(), b'0'),
(10100000050002, 10100000010002, '技术总监，负责架构设计', '["CTO", "架构师"]', '渡山科技总部', '["Python", "Go", "微服务", "K8s"]', '技术架构设计与团队管理', '微服务架构、云原生', 'technical', '{"response_style": "concise", "preferred_format": "list", "language": "zh-CN", "tone": "professional", "auto_summary": false}', '1', 'system', NOW(), 'system', NOW(), b'0'),
(10100000050003, 10100000010003, '项目经理，负责项目交付', '["PM", "敏捷"]', '渡山科技总部', '["项目管理", "Scrum", "JIRA"]', '项目交付与团队协调', '敏捷项目管理', 'formal', '{"response_style": "balanced", "preferred_format": "paragraph", "language": "zh-CN", "tone": "friendly", "auto_summary": true}', '1', 'system', NOW(), 'system', NOW(), b'0'),
(10100000050004, 10100000010004, '全栈开发工程师', '["开发", "前端"]', '渡山科技总部', '["Vue3", "TypeScript", "Python"]', '前后端功能开发', '前端工程化、组件开发', 'casual', NULL, '1', 'system', NOW(), 'system', NOW(), b'0'),
(10100000050005, 10100000010005, '运维工程师，负责部署运维', '["运维", "DevOps"]', '渡山科技总部', '["Docker", "K8s", "CI/CD", "Linux"]', '基础设施运维与自动化', '容器化部署、监控告警', 'technical', NULL, '1', 'system', NOW(), 'system', NOW(), b'0');

INSERT IGNORE INTO `system_user_post` (`id`, `user_id`, `post_id`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `tenant_id`) VALUES
(10100000060001, 10100000010001, 10100000030001, 'system', NOW(), 'system', NOW(), b'0', '1'),
(10100000060002, 10100000010002, 10100000030002, 'system', NOW(), 'system', NOW(), b'0', '1'),
(10100000060003, 10100000010003, 10100000030003, 'system', NOW(), 'system', NOW(), b'0', '1'),
(10100000060004, 10100000010004, 10100000030004, 'system', NOW(), 'system', NOW(), b'0', '1'),
(10100000060005, 10100000010005, 10100000030005, 'system', NOW(), 'system', NOW(), b'0', '1');

INSERT IGNORE INTO `system_user_role` (`id`, `user_id`, `role_id`, `tenant_id`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10100000070001, 10100000010001, 10100000040001, '1', 'system', NOW(), 'system', NOW(), b'0'),
(10100000070002, 10100000010002, 10100000040002, '1', 'system', NOW(), 'system', NOW(), b'0'),
(10100000070003, 10100000010003, 10100000040002, '1', 'system', NOW(), 'system', NOW(), b'0'),
(10100000070004, 10100000010004, 10100000040003, '1', 'system', NOW(), 'system', NOW(), b'0'),
(10100000070005, 10100000010005, 10100000040002, '1', 'system', NOW(), 'system', NOW(), b'0');

INSERT IGNORE INTO `system_oauth2_client` (`id`, `client_id`, `secret`, `name`, `logo`, `description`, `status`, `user_type`, `access_token_validity_seconds`, `refresh_token_validity_seconds`, `redirect_uris`, `authorized_grant_types`, `scopes`, `auto_approve_scopes`, `authorities`, `resource_ids`, `additional_information`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `credential_revision`) VALUES
(10100000080001, 'default', 'dushan-admin-secret', '渡山管理后台', '', '默认管理后台客户端', 1, 2, 1800, 2592000, '["http://localhost"]', '["password", "authorization_code", "refresh_token", "implicit"]', '["user.read", "user.write"]', '["user.read"]', '[]', '[]', NULL, 'system', NOW(), 'system', NOW(), b'0', 1);

INSERT IGNORE INTO `system_notification_notice` (`id`, `code`, `title`, `content`, `type`, `user_type`, `channels`, `sms_template_code`, `mail_account_id`, `publisher`, `status`, `tenant_id`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10100000100001, 'system_announcement_publish', '公告', '<p>这是一个公告。</p>', 1, 2, '["INTERNAL"]', 'system-notice', 10100000085001, '渡山', 1, '1', '10100000010001', '2026-02-14 10:56:36', '10100000010001', '2026-02-14 12:48:24', b'0');

INSERT IGNORE INTO system_authorization_revision (id, revision, creator, updater, create_time, update_time, deleted) VALUES (1, 1, '', '', UTC_TIMESTAMP(), UTC_TIMESTAMP(), 0);
