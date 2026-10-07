-- 由 mysql/system/01_system_data.sql 生成；请修改 MySQL 源文件后重新生成。

-- 仅用于空库首次初始化，不支持重复执行。

SET IDENTITY_INSERT system_tenant_package ON;

INSERT INTO system_tenant_package (id, name, status, remark, menu_ids, creator, create_time, updater, update_time, deleted) VALUES
(10100000090001, '标准套餐', 1, '包含系统管理与基础设施全部功能', '[10000000000001,10000000000101,10000000000102,10000000000103,10000000000104,10000000000105,10000000000106,10000000000107,10000000000108,10000000000201,10000000000202,10000000000203,10000000000204,10000000000205,10000000000206,10000000000207,10000000000208,10000000000209,10000000000301,10000000000302,10000000000303,10000000000304,10000000000305,10000000000401,10000000000402,10000000000403,10000000000404,10000000000405,10000000000501,10000000000502,10000000000503,10000000000504,10000000000505,10000000000506,10000000000601,10000000000602,10000000000603,10000000000604,10000000000605,10000000000606,10000000000701,10000000000711,10000000000712,10000000000713,10000000000714,10000000000715,10000000000716,10000000000721,10000000000722,10000000000732,10000000000741,10000000000742,10000000000743,10000000000744,10000000000745,10000000000801,10000000000901,10000000001001,10000000001011,10000000001012,10000000001013,10000000001014,10000000001015,10000000001016,10000000001021,10000000001022,10000000001023,10000000001024,10000000001025,10000000001026,10000000001027,10000000001031,10000000001032,10000000001033,10000000001101,10000000001111,10000000001112,10000000001113,10000000001114,10000000001115,10000000001121,10000000001122,10000000001123,10000000001124,10000000001125,10000000001126,10000000001127,10000000001131,10000000001132,10000000001133,10000000001201,10000000001202,10000000001203,10000000001204,10000000001205,10000000001206,10000000001301,10000000001302,10000000001303,10000000001304,10000000001305,10000000001306,10000000001401,10000000001411,10000000001412,10000000001413,10000000001414,10000000001415,10000000001421,10000000001422,10000000001423,10000000001501,10000000001511,10000000001512,10000000001513,10000000001514,10000000001515,10000000001516,10000000001521,10000000001522,10000000001601,10000000001602,10000000001701,10000000001702,10000000001703,10000000001801,10000000001802,10000000001803,10000000002001,10000000100001,10000000100101,10000000100112,10000000100113,10000000100114,10000000100115,10000000100116,10000000100122,10000000100123,10000000100124,10000000100125,10000000100126,10000000100201,10000000100211,10000000100212,10000000100213,10000000100214,10000000100215,10000000100216,10000000100221,10000000100222,10000000100223,10000000100224,10000000100225,10000000100301,10000000100312,10000000100313,10000000100314,10000000100315,10000000100316,10000000100317,10000000100401,10000000100412,10000000100413,10000000100414,10000000100415,10000000100416,10000000100417,10000000100418,10000000100501,10000000100502,10000000100503,10000000100504,10000000100505,10000000100506,10000000100601,10000000100611,10000000100612,10000000100613,10000000100621,10000000100622,10000000100623,10000000100624,10000000100701,10000000100711,10000000100712,10000000100721,10000000100722,10000000100731,10000000100732,10000000100741,10000000100742,10000000100743,10000000100801,10000000100802,10000000100803,10000000100901,10000000100902,10000000100903,10000000100904,10000000100905,10000000100906,10000000100907,10000000101001,10000000101101,10000000101201]', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

SET IDENTITY_INSERT system_tenant_package OFF;

SET IDENTITY_INSERT system_tenant ON;

INSERT INTO system_tenant (id, name, contact_user_id, contact_name, contact_mobile, status, websites, package_id, expire_time, account_count, creator, create_time, updater, update_time, deleted) VALUES
(1, '渡山无界', 10100000010001, '管理员', '19053131342', 1, '["http://localhost"]', 10100000090001, '2099-12-31 23:59:59', 9999, 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

SET IDENTITY_INSERT system_tenant OFF;

SET IDENTITY_INSERT system_dept ON;

INSERT INTO system_dept (id, name, parent_id, sort, leader_user_id, phone, email, status, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000020001, '渡山无界', 0, 1, 10100000010001, '19053131342', '729227973@qq.com', 1, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_dept (id, name, parent_id, sort, leader_user_id, phone, email, status, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000020002, '技术部', 10100000020001, 1, NULL, NULL, NULL, 1, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_dept (id, name, parent_id, sort, leader_user_id, phone, email, status, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000020003, '产品部', 10100000020001, 2, NULL, NULL, NULL, 1, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_dept (id, name, parent_id, sort, leader_user_id, phone, email, status, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000020004, '运营部', 10100000020001, 3, NULL, NULL, NULL, 1, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

SET IDENTITY_INSERT system_dept OFF;

SET IDENTITY_INSERT system_post ON;

INSERT INTO system_post (id, code, name, sort, status, remark, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000030001, 'CEO', '董事长', 1, 1, NULL, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_post (id, code, name, sort, status, remark, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000030002, 'CTO', '技术总监', 2, 1, NULL, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_post (id, code, name, sort, status, remark, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000030003, 'PM', '项目经理', 3, 1, NULL, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_post (id, code, name, sort, status, remark, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000030004, 'DEV', '开发工程师', 4, 1, NULL, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_post (id, code, name, sort, status, remark, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000030005, 'OPS', '运维工程师', 5, 1, NULL, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

SET IDENTITY_INSERT system_post OFF;

SET IDENTITY_INSERT system_role ON;

INSERT INTO system_role (id, name, code, sort, data_scope, data_scope_dept_ids, builtin, status, remark, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000040001, '超级管理员', 'super_admin', 1, 1, '[]', 1, 1, '超级管理员，拥有所有权限', '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role (id, name, code, sort, data_scope, data_scope_dept_ids, builtin, status, remark, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000040002, '普通角色', 'common', 2, 1, '[]', 1, 1, '普通角色，仅查看权限', '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role (id, name, code, sort, data_scope, data_scope_dept_ids, builtin, status, remark, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000040003, '只读演示', 'readonly', 3, 1, '[]', 2, 1, '只读演示，仅查看权限', '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

SET IDENTITY_INSERT system_role OFF;

SET IDENTITY_INSERT system_users ON;

INSERT INTO system_users (id, username, password, nickname, remark, dept_id, post_ids, email, mobile, sex, avatar, status, login_ip, login_date, tenant_id, creator, create_time, updater, update_time, deleted, credential_revision, authorization_revision) VALUES
(10100000010001, 'admin', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '管理员', '超级管理员', 10100000020001, '[10100000030001]', '729227973@qq.com', '19053131342', 0, '', 1, '127.0.0.1', GETUTCDATE(), '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0, 1, 1);

INSERT INTO system_users (id, username, password, nickname, remark, dept_id, post_ids, email, mobile, sex, avatar, status, login_ip, login_date, tenant_id, creator, create_time, updater, update_time, deleted, credential_revision, authorization_revision) VALUES
(10100000010002, 'dushan', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '渡山', '技术总监', 10100000020002, '[10100000030002]', 'dushan@dushan.com', '13800138001', 1, '', 1, '', NULL, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0, 1, 1);

INSERT INTO system_users (id, username, password, nickname, remark, dept_id, post_ids, email, mobile, sex, avatar, status, login_ip, login_date, tenant_id, creator, create_time, updater, update_time, deleted, credential_revision, authorization_revision) VALUES
(10100000010003, 'zhangsan', '$2b$12$sbsUEwky022MhfFxADSpCexYXPL9bp8Gn.Kk/0zVnQTnm4pq9l8ce', '张三', '项目经理', 10100000020002, '[10100000030003]', 'zhangsan@dushan.com', '13800138002', 1, '', 1, '', NULL, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0, 1, 1);

INSERT INTO system_users (id, username, password, nickname, remark, dept_id, post_ids, email, mobile, sex, avatar, status, login_ip, login_date, tenant_id, creator, create_time, updater, update_time, deleted, credential_revision, authorization_revision) VALUES
(10100000010004, 'demo', '$2b$12$Uctklxw9DE6/qcfd2kp4x.CuEUssMoofLKxy5xH5pAld/9BBwQ6ky', '演示用户', '只读演示账号', 10100000020001, '[]', NULL, NULL, 0, '', 1, '', NULL, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0, 1, 1);

SET IDENTITY_INSERT system_users OFF;

SET IDENTITY_INSERT system_user_profiles ON;

INSERT INTO system_user_profiles (id, user_id, bio, tags, address, skills, work_scope, expertise, communication_style, ai_preference, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000050001, 10100000010001, '系统超级管理员', '["管理员", "全栈"]', '渡山无界总部', '["Python", "FastAPI", "Vue3"]', '系统架构设计与全局管理', '全栈开发、系统架构', 'technical', '{"response_style": "detailed", "preferred_format": "table", "language": "zh-CN", "tone": "professional", "auto_summary": true}', '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_user_profiles (id, user_id, bio, tags, address, skills, work_scope, expertise, communication_style, ai_preference, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000050002, 10100000010002, '技术总监，负责架构设计', '["CTO", "架构师"]', '渡山无界总部', '["Python", "Go", "微服务", "K8s"]', '技术架构设计与团队管理', '微服务架构、云原生', 'technical', '{"response_style": "concise", "preferred_format": "list", "language": "zh-CN", "tone": "professional", "auto_summary": false}', '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_user_profiles (id, user_id, bio, tags, address, skills, work_scope, expertise, communication_style, ai_preference, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000050003, 10100000010003, '项目经理，负责项目交付', '["PM", "敏捷"]', '渡山无界总部', '["项目管理", "Scrum", "JIRA"]', '项目交付与团队协调', '敏捷项目管理', 'formal', '{"response_style": "balanced", "preferred_format": "paragraph", "language": "zh-CN", "tone": "friendly", "auto_summary": true}', '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_user_profiles (id, user_id, bio, tags, address, skills, work_scope, expertise, communication_style, ai_preference, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000050004, 10100000010004, '只读演示账号，用于查看业务功能', '["演示"]', '渡山无界总部', '[]', '查看系统功能演示', '只读浏览', 'formal', '{"response_style": "balanced", "preferred_format": "paragraph", "language": "zh-CN", "tone": "friendly", "auto_summary": false}', '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

SET IDENTITY_INSERT system_user_profiles OFF;

SET IDENTITY_INSERT system_user_post ON;

INSERT INTO system_user_post (id, user_id, post_id, creator, create_time, updater, update_time, deleted, tenant_id) VALUES
(10100000060001, 10100000010001, 10100000030001, 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0, '1');

INSERT INTO system_user_post (id, user_id, post_id, creator, create_time, updater, update_time, deleted, tenant_id) VALUES
(10100000060002, 10100000010002, 10100000030002, 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0, '1');

INSERT INTO system_user_post (id, user_id, post_id, creator, create_time, updater, update_time, deleted, tenant_id) VALUES
(10100000060003, 10100000010003, 10100000030003, 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0, '1');

SET IDENTITY_INSERT system_user_post OFF;

SET IDENTITY_INSERT system_user_role ON;

INSERT INTO system_user_role (id, user_id, role_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000070001, 10100000010001, 10100000040001, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_user_role (id, user_id, role_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000070002, 10100000010002, 10100000040002, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_user_role (id, user_id, role_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000070003, 10100000010003, 10100000040002, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_user_role (id, user_id, role_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000070004, 10100000010004, 10100000040003, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

SET IDENTITY_INSERT system_user_role OFF;

SET IDENTITY_INSERT system_role_menu ON;

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075001, 10100000040002, 10000000000001, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075002, 10100000040002, 10000000000101, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075003, 10100000040002, 10000000000102, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075004, 10100000040002, 10000000000201, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075005, 10100000040002, 10000000000202, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075006, 10100000040002, 10000000000301, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075007, 10100000040002, 10000000000302, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075008, 10100000040002, 10000000000401, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075009, 10100000040002, 10000000000402, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075010, 10100000040002, 10000000000501, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075011, 10100000040002, 10000000000502, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075012, 10100000040002, 10000000000601, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075013, 10100000040002, 10000000000602, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075014, 10100000040002, 10000000000701, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075015, 10100000040002, 10000000000711, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075016, 10100000040002, 10000000000712, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075017, 10100000040002, 10000000000721, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075018, 10100000040002, 10000000000722, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075019, 10100000040002, 10000000000732, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075020, 10100000040002, 10000000000741, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075021, 10100000040002, 10000000000742, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075022, 10100000040002, 10000000000801, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075023, 10100000040002, 10000000000901, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075024, 10100000040002, 10000000001001, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075025, 10100000040002, 10000000001011, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075026, 10100000040002, 10000000001012, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075027, 10100000040002, 10000000001021, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075028, 10100000040002, 10000000001022, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075030, 10100000040002, 10000000001101, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075031, 10100000040002, 10000000001111, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075032, 10100000040002, 10000000001112, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075033, 10100000040002, 10000000001121, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075034, 10100000040002, 10000000001122, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075036, 10100000040002, 10000000001201, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075037, 10100000040002, 10000000001202, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075038, 10100000040002, 10000000001301, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075039, 10100000040002, 10000000001302, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075040, 10100000040002, 10000000001401, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075041, 10100000040002, 10000000001411, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075042, 10100000040002, 10000000001412, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075043, 10100000040002, 10000000001421, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075044, 10100000040002, 10000000001422, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075045, 10100000040002, 10000000001501, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075046, 10100000040002, 10000000001511, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075047, 10100000040002, 10000000001512, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075048, 10100000040002, 10000000001521, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075049, 10100000040002, 10000000001522, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075050, 10100000040002, 10000000001601, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075051, 10100000040002, 10000000001602, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075052, 10100000040002, 10000000001701, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075053, 10100000040002, 10000000001702, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075054, 10100000040002, 10000000001801, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075055, 10100000040002, 10000000001802, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075056, 10100000040002, 10000000002001, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075057, 10100000040002, 10000000100001, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075060, 10100000040002, 10000000100201, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075061, 10100000040002, 10000000100211, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075062, 10100000040002, 10000000100212, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075063, 10100000040002, 10000000100221, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075064, 10100000040002, 10000000100222, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075065, 10100000040002, 10000000100301, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075066, 10100000040002, 10000000100401, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075067, 10100000040002, 10000000100412, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075068, 10100000040002, 10000000100418, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075071, 10100000040002, 10000000100601, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075072, 10100000040002, 10000000100611, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075073, 10100000040002, 10000000100612, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075074, 10100000040002, 10000000100621, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075075, 10100000040002, 10000000100622, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075076, 10100000040002, 10000000100701, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075077, 10100000040002, 10000000100711, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075078, 10100000040002, 10000000100712, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075079, 10100000040002, 10000000100721, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075080, 10100000040002, 10000000100722, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075082, 10100000040002, 10000000100741, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075083, 10100000040002, 10000000100742, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075084, 10100000040002, 10000000100801, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075085, 10100000040002, 10000000100802, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075086, 10100000040002, 10000000100901, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075087, 10100000040002, 10000000100902, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075088, 10100000040002, 10000000100907, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075089, 10100000040002, 10000000101001, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075090, 10100000040002, 10000000101101, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075091, 10100000040002, 10000000101201, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075092, 10100000040003, 10000000000001, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075093, 10100000040003, 10000000000101, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075094, 10100000040003, 10000000000102, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075095, 10100000040003, 10000000000201, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075096, 10100000040003, 10000000000202, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075097, 10100000040003, 10000000000301, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075098, 10100000040003, 10000000000302, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075099, 10100000040003, 10000000000401, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075100, 10100000040003, 10000000000402, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075101, 10100000040003, 10000000000501, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075102, 10100000040003, 10000000000502, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075103, 10100000040003, 10000000000601, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075104, 10100000040003, 10000000000602, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075105, 10100000040003, 10000000000701, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075106, 10100000040003, 10000000000711, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075107, 10100000040003, 10000000000712, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075108, 10100000040003, 10000000000721, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075109, 10100000040003, 10000000000722, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075110, 10100000040003, 10000000000732, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075111, 10100000040003, 10000000000741, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075112, 10100000040003, 10000000000742, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075113, 10100000040003, 10000000000801, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075114, 10100000040003, 10000000000901, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075115, 10100000040003, 10000000001001, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075116, 10100000040003, 10000000001011, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075117, 10100000040003, 10000000001012, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075118, 10100000040003, 10000000001021, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075119, 10100000040003, 10000000001022, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075121, 10100000040003, 10000000001101, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075122, 10100000040003, 10000000001111, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075123, 10100000040003, 10000000001112, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075124, 10100000040003, 10000000001121, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075125, 10100000040003, 10000000001122, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075127, 10100000040003, 10000000001201, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075128, 10100000040003, 10000000001202, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075129, 10100000040003, 10000000001301, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075130, 10100000040003, 10000000001302, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075131, 10100000040003, 10000000001401, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075132, 10100000040003, 10000000001411, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075133, 10100000040003, 10000000001412, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075134, 10100000040003, 10000000001421, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075135, 10100000040003, 10000000001422, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075136, 10100000040003, 10000000001501, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075137, 10100000040003, 10000000001511, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075138, 10100000040003, 10000000001512, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075139, 10100000040003, 10000000001521, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075140, 10100000040003, 10000000001522, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075141, 10100000040003, 10000000001601, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075142, 10100000040003, 10000000001602, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075143, 10100000040003, 10000000001701, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075144, 10100000040003, 10000000001702, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075145, 10100000040003, 10000000001801, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075146, 10100000040003, 10000000001802, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075147, 10100000040003, 10000000002001, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075148, 10100000040003, 10000000100001, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075151, 10100000040003, 10000000100201, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075152, 10100000040003, 10000000100211, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075153, 10100000040003, 10000000100212, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075154, 10100000040003, 10000000100221, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075155, 10100000040003, 10000000100222, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075156, 10100000040003, 10000000100301, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075157, 10100000040003, 10000000100401, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075158, 10100000040003, 10000000100412, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075159, 10100000040003, 10000000100418, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075162, 10100000040003, 10000000100601, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075163, 10100000040003, 10000000100611, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075164, 10100000040003, 10000000100612, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075165, 10100000040003, 10000000100621, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075166, 10100000040003, 10000000100622, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075167, 10100000040003, 10000000100701, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075168, 10100000040003, 10000000100711, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075169, 10100000040003, 10000000100712, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075170, 10100000040003, 10000000100721, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075171, 10100000040003, 10000000100722, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075173, 10100000040003, 10000000100741, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075174, 10100000040003, 10000000100742, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075175, 10100000040003, 10000000100801, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075176, 10100000040003, 10000000100802, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075177, 10100000040003, 10000000100901, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075178, 10100000040003, 10000000100902, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075179, 10100000040003, 10000000100907, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075180, 10100000040003, 10000000101001, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075181, 10100000040003, 10000000101101, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075182, 10100000040003, 10000000101201, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075183, 10100000040002, 10000000100312, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

INSERT INTO system_role_menu (id, role_id, menu_id, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000075184, 10100000040003, 10000000100312, '1', 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0);

SET IDENTITY_INSERT system_role_menu OFF;

SET IDENTITY_INSERT system_oauth2_client ON;

INSERT INTO system_oauth2_client (id, client_id, secret, name, logo, description, status, user_type, access_token_validity_seconds, refresh_token_validity_seconds, redirect_uris, authorized_grant_types, scopes, auto_approve_scopes, authorities, resource_ids, additional_information, creator, create_time, updater, update_time, deleted, credential_revision) VALUES
(10100000080001, 'default', 'dushan-admin-secret', '渡山管理后台', '', '默认管理后台客户端', 1, 2, 1800, 2592000, '["http://localhost"]', '["password", "authorization_code", "refresh_token", "implicit"]', '["user.read", "user.write"]', '["user.read"]', '[]', '[]', NULL, 'system', GETUTCDATE(), 'system', GETUTCDATE(), 0, 1);

SET IDENTITY_INSERT system_oauth2_client OFF;

SET IDENTITY_INSERT system_notification_notice ON;

INSERT INTO system_notification_notice (id, code, title, content, type, user_type, channels, sms_template_code, mail_account_id, publisher, status, builtin, tenant_id, creator, create_time, updater, update_time, deleted) VALUES
(10100000100001, 'system_announcement_publish', '公告', '<p>这是一个公告。</p>', 1, 2, '["INTERNAL"]', 'system-notice', 10100000085001, '渡山', 1, 1, '1', '10100000010001', '2026-02-14 10:56:36', '10100000010001', '2026-02-14 12:48:24', 0);

SET IDENTITY_INSERT system_notification_notice OFF;

SET IDENTITY_INSERT system_authorization_revision ON;

INSERT INTO system_authorization_revision (id, revision, creator, updater, create_time, update_time, deleted) VALUES
(1, 1, '', '', GETUTCDATE(), GETUTCDATE(), 0);

SET IDENTITY_INSERT system_authorization_revision OFF;
