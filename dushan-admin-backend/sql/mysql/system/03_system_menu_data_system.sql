-- 由 simple 业务初始数据适配 Native；默认账号密码 admin123，bcrypt cost=12。

SET NAMES utf8mb4;

SET time_zone = '+00:00';

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000001, '系统管理', '', 101000000, 0, '/system', 'ep:tools', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'group', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000101, '用户管理', '', 101010000, 10000000000001, 'user', 'ep:user', 'system/user/index', 'SystemUser', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000102, '用户查询', 'system:user:query', 101010001, 10000000000101, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000103, '用户新增', 'system:user:create', 101010002, 10000000000101, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000104, '用户修改', 'system:user:update', 101010003, 10000000000101, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000105, '用户删除', 'system:user:delete', 101010004, 10000000000101, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000106, '用户导出', 'system:user:export', 101010005, 10000000000101, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000107, '用户导入', 'system:user:import', 101010006, 10000000000101, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000108, '重置密码', 'system:user:update-password', 101010007, 10000000000101, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000201, '角色管理', '', 101020000, 10000000000001, 'role', 'ep:user-filled', 'system/role/index', 'SystemRole', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000202, '角色查询', 'system:permission:role:query', 101020001, 10000000000201, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000203, '角色新增', 'system:permission:role:create', 101020002, 10000000000201, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000204, '角色修改', 'system:permission:role:update', 101020003, 10000000000201, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000205, '角色删除', 'system:permission:role:delete', 101020004, 10000000000201, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000206, '角色导出', 'system:permission:role:export', 101020005, 10000000000201, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000207, '分配菜单', 'system:permission:assign-role-menu', 101020006, 10000000000201, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000208, '分配数据权限', 'system:permission:assign-role-data-scope', 101020007, 10000000000201, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000209, '分配用户角色', 'system:permission:assign-user-role', 101020008, 10000000000201, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000301, '菜单管理', '', 101030000, 10000000000001, 'menu', 'ep:menu', 'system/menu/index', 'SystemMenu', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000302, '菜单查询', 'system:permission:menu:query', 101030001, 10000000000301, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000303, '菜单新增', 'system:permission:menu:create', 101030002, 10000000000301, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000304, '菜单修改', 'system:permission:menu:update', 101030003, 10000000000301, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000305, '菜单删除', 'system:permission:menu:delete', 101030004, 10000000000301, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000401, '部门管理', '', 101040000, 10000000000001, 'dept', 'ep:office-building', 'system/dept/index', 'SystemDept', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000402, '部门查询', 'system:dept:query', 101040001, 10000000000401, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000403, '部门新增', 'system:dept:create', 101040002, 10000000000401, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000404, '部门修改', 'system:dept:update', 101040003, 10000000000401, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000405, '部门删除', 'system:dept:delete', 101040004, 10000000000401, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000501, '岗位管理', '', 101050000, 10000000000001, 'post', 'ep:postcard', 'system/post/index', 'SystemPost', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000502, '岗位查询', 'system:dept:post:query', 101050001, 10000000000501, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000503, '岗位新增', 'system:dept:post:create', 101050002, 10000000000501, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000504, '岗位修改', 'system:dept:post:update', 101050003, 10000000000501, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000505, '岗位删除', 'system:dept:post:delete', 101050004, 10000000000501, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000506, '岗位导出', 'system:dept:post:export', 101050005, 10000000000501, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000601, '字典管理', '', 101060000, 10000000000001, 'dict', 'ep:collection', 'system/dict/index', 'SystemDict', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000602, '字典查询', 'system:dict:query', 101060001, 10000000000601, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000603, '字典新增', 'system:dict:create', 101060002, 10000000000601, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000604, '字典修改', 'system:dict:update', 101060003, 10000000000601, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000605, '字典删除', 'system:dict:delete', 101060004, 10000000000601, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000606, '字典导出', 'system:dict:export', 101060005, 10000000000601, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000701, '通知中心', '', 101070000, 10000000000001, 'notification', 'ep:bell', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'group', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000711, '通知管理', '', 101070100, 10000000000701, 'notice', 'ep:promotion', 'system/notification/notice/index', 'SystemNotice', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000712, '通知查询', 'system:notification:query', 101070101, 10000000000711, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000713, '通知新增', 'system:notification:create', 101070102, 10000000000711, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000714, '通知修改', 'system:notification:update', 101070103, 10000000000711, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000715, '通知删除', 'system:notification:delete', 101070104, 10000000000711, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000716, '通知推送', 'system:notification:send', 101070105, 10000000000711, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000721, '通知日志', '', 101070200, 10000000000701, 'notice-log', 'ep:document-copy', 'system/notification/notice-log/index', 'SystemNoticeLog', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000722, '通知日志查询', 'system:notification:log:query', 101070201, 10000000000721, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000731, '我的站内信', '', 101070300, 10000000000701, 'notice-message', 'ep:message', 'system/notification/notice-message/index', 'SystemNoticeMessage', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000732, '消息查询', 'system:notification:message:query', 101070301, 10000000000731, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000741, '系统公告', '', 101070400, 10000000000001, 'announcement', 'ep:notification', 'system/announcement/index', 'SystemAnnouncement', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000742, '公告查询', 'system:announcement:query', 101070401, 10000000000741, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000743, '公告新增', 'system:announcement:create', 101070402, 10000000000741, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000744, '公告修改', 'system:announcement:update', 101070403, 10000000000741, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000000745, '公告删除', 'system:announcement:delete', 101070404, 10000000000741, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000801, '消息管理', '', 101080000, 10000000000001, 'message', 'ep:chat-dot-round', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'group', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001001, '邮件管理', '', 101080100, 10000000000801, 'mail', 'ep:message', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'group', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001011, '邮箱账号', '', 101100100, 10000000001001, 'account', 'ep:user', 'system/mail/account/index', 'SystemMailAccount', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001012, '账号查询', 'system:mail:account:query', 101100101, 10000000001011, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001013, '账号新增', 'system:mail:account:create', 101100102, 10000000001011, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001014, '账号修改', 'system:mail:account:update', 101100103, 10000000001011, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001015, '账号删除', 'system:mail:account:delete', 101100104, 10000000001011, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001016, '账号导出', 'system:mail:account:export', 101100105, 10000000001011, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001021, '邮件模板', '', 101100200, 10000000001001, 'template', 'ep:document', 'system/mail/template/index', 'SystemMailTemplate', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001022, '模板查询', 'system:mail:template:query', 101100201, 10000000001021, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001023, '模板新增', 'system:mail:template:create', 101100202, 10000000001021, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001024, '模板修改', 'system:mail:template:update', 101100203, 10000000001021, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001025, '模板删除', 'system:mail:template:delete', 101100204, 10000000001021, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001026, '模板导出', 'system:mail:template:export', 101100205, 10000000001021, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001027, '发送测试', 'system:mail:template:send-mail', 101100206, 10000000001021, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001031, '邮件日志', '', 101100300, 10000000001001, 'log', 'ep:notebook', 'system/mail/log/index', 'SystemMailLog', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001032, '日志查询', 'system:mail:log:query', 101100301, 10000000001031, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001033, '日志导出', 'system:mail:log:export', 101100302, 10000000001031, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001101, '短信管理', '', 101080200, 10000000000801, 'sms', 'ep:iphone', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'group', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001111, '短信渠道', '', 101110100, 10000000001101, 'channel', 'ep:connection', 'system/sms/channel/index', 'SystemSmsChannel', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001112, '渠道查询', 'system:sms:channel:query', 101110101, 10000000001111, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001113, '渠道新增', 'system:sms:channel:create', 101110102, 10000000001111, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001114, '渠道修改', 'system:sms:channel:update', 101110103, 10000000001111, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001115, '渠道删除', 'system:sms:channel:delete', 101110104, 10000000001111, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001121, '短信模板', '', 101110200, 10000000001101, 'template', 'ep:document', 'system/sms/template/index', 'SystemSmsTemplate', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001122, '模板查询', 'system:sms:template:query', 101110201, 10000000001121, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001123, '模板新增', 'system:sms:template:create', 101110202, 10000000001121, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001124, '模板修改', 'system:sms:template:update', 101110203, 10000000001121, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001125, '模板删除', 'system:sms:template:delete', 101110204, 10000000001121, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001126, '模板导出', 'system:sms:template:export', 101110205, 10000000001121, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001127, '发送测试', 'system:sms:template:send-sms', 101110206, 10000000001121, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001131, '短信日志', '', 101110300, 10000000001101, 'log', 'ep:notebook', 'system/sms/log/index', 'SystemSmsLog', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001132, '日志查询', 'system:sms:log:query', 101110301, 10000000001131, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001133, '日志导出', 'system:sms:log:export', 101110302, 10000000001131, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000000901, '租户管理', '', 101090000, 10000000000001, 'tenant-manage', 'ep:house', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'group', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001201, '租户列表', '', 101090100, 10000000000901, 'tenant', 'ep:list', 'system/tenant/index', 'SystemTenant', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001202, '租户查询', 'system:tenant:query', 101120001, 10000000001201, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001203, '租户新增', 'system:tenant:create', 101120002, 10000000001201, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001204, '租户修改', 'system:tenant:update', 101120003, 10000000001201, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001205, '租户删除', 'system:tenant:delete', 101120004, 10000000001201, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001206, '租户导出', 'system:tenant:export', 101120005, 10000000001201, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001301, '租户套餐', '', 101090200, 10000000000901, 'tenantPackage', 'ep:goods', 'system/tenantPackage/index', 'SystemTenantPackage', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001302, '套餐查询', 'system:tenant:package:query', 101130001, 10000000001301, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001303, '套餐新增', 'system:tenant:package:create', 101130002, 10000000001301, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001304, '套餐修改', 'system:tenant:package:update', 101130003, 10000000001301, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001305, '套餐删除', 'system:tenant:package:delete', 101130004, 10000000001301, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001306, '套餐导出', 'system:tenant:package:export', 101130005, 10000000001301, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001401, 'OAuth2 管理', '', 101140000, 10000000000001, 'oauth2', 'ep:lock', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'group', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001411, 'OAuth2 客户端', '', 101140100, 10000000001401, 'client', 'ep:monitor', 'system/oauth2/client/index', 'SystemOAuth2Client', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001412, '客户端查询', 'system:oauth2:client:query', 101140101, 10000000001411, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001413, '客户端新增', 'system:oauth2:client:create', 101140102, 10000000001411, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001414, '客户端修改', 'system:oauth2:client:update', 101140103, 10000000001411, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001415, '客户端删除', 'system:oauth2:client:delete', 101140104, 10000000001411, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001421, 'OAuth2 令牌', '', 101140200, 10000000001401, 'token', 'ep:key', 'system/oauth2/token/index', 'SystemOAuth2Token', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001422, '令牌查询', 'system:oauth2:token:page', 101140201, 10000000001421, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001423, '令牌删除', 'system:oauth2:token:delete', 101140202, 10000000001421, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001501, '三方登录', '', 101150000, 10000000000001, 'social', 'ep:share', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'group', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001511, '社交客户端', '', 101150100, 10000000001501, 'client', 'ep:link', 'system/social/client/index', 'SystemSocialClient', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001512, '客户端查询', 'system:social:client:query', 101150101, 10000000001511, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001513, '客户端新增', 'system:social:client:create', 101150102, 10000000001511, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001514, '客户端修改', 'system:social:client:update', 101150103, 10000000001511, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001515, '客户端删除', 'system:social:client:delete', 101150104, 10000000001511, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001516, '发送订阅消息', 'system:social:client:send-subscribe-message', 101150105, 10000000001511, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001521, '社交用户', '', 101150200, 10000000001501, 'user', 'ep:avatar', 'system/social/user/index', 'SystemSocialUser', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001522, '用户查询', 'system:social:user:query', 101150201, 10000000001521, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001601, '地区管理', '', 101160000, 10000000000001, 'area', 'ep:location', 'system/area/index', 'SystemArea', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001602, '地区查询', 'system:area:query', 101160001, 10000000001601, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000002001, '审计日志', '', 101200000, 10000000000001, 'audit', 'ep:document-checked', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'group', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001701, '登录日志', '', 101200100, 10000000002001, 'loginlog', 'ep:tickets', 'system/loginlog/index', 'SystemLoginLog', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001702, '日志查询', 'system:logger:login-log:query', 101170001, 10000000001701, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001703, '日志导出', 'system:logger:login-log:export', 101170002, 10000000001701, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001801, '操作日志', '', 101200200, 10000000002001, 'operatelog', 'ep:operation', 'system/operatelog/index', 'SystemOperateLog', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000001802, '日志查询', 'system:logger:operate-log:query', 101180001, 10000000001801, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000001803, '日志导出', 'system:logger:operate-log:export', 101180002, 10000000001801, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);
