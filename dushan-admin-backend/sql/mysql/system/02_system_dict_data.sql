-- 由 simple 业务初始数据适配 Native；默认账号密码 admin123，bcrypt cost=12。

SET NAMES utf8mb4;

SET time_zone = '+00:00';

INSERT IGNORE INTO `system_dict_type` (`id`, `name`, `type`, `status`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000010001, '布尔字符串', 'infra_boolean_string', 1, '基础设施 - 布尔值字符串', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010002, '参数配置类型', 'infra_config_type', 1, '基础设施 - 参数配置类型', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010003, '数据源主从类型', 'infra_data_source_type', 1, '基础设施 - 数据源主从类型', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010004, '文件存储器', 'infra_file_storage', 1, '基础设施 - 文件存储器', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010005, '任务日志状态', 'infra_job_log_status', 1, '基础设施 - 定时任务日志状态', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010006, '任务状态', 'infra_job_status', 1, '基础设施 - 定时任务状态', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010007, 'MQ 日志状态', 'infra_mq_log_status', 1, '基础设施 - MQ 消费日志状态', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010008, '操作类型', 'infra_operate_type', 1, '基础设施 - 操作日志的操作类型', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010009, '数据源健康状态', 'infra_data_source_health_status', 1, '基础设施 - 数据源健康状态', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010010, '负载均衡策略', 'infra_load_balancer_strategy', 1, '基础设施 - 数据源负载均衡策略', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010011, 'API错误日志处理状态', 'infra_api_error_log_process_status', 1, '基础设施 - API 错误日志的处理状态', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010012, '代码生成模板类型', 'infra_codegen_template_type', 1, '基础设施 - 代码生成模板类型', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010013, '代码生成前端类型', 'infra_codegen_front_type', 1, '基础设施 - 代码生成前端类型', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010014, '代码生成场景', 'infra_codegen_scene', 1, '基础设施 - 代码生成场景', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010015, '配置所属模块', 'infra_config_module', 1, '基础设施 - 配置中心模块标识', 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_type` (`id`, `name`, `type`, `status`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000010101, '用户类型', 'user_type', 1, '通用 - 用户类型', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010102, '系统状态', 'common_status', 1, '通用 - 系统开关状态', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010103, '用户性别', 'system_user_sex', 1, '系统 - 用户性别', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010104, '数据权限范围', 'system_data_scope', 1, '系统 - 数据权限范围', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010105, '登录日志类型', 'system_login_type', 1, '系统 - 登录日志的类型', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010106, '登录结果', 'system_login_result', 1, '系统 - 登录结果', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010107, '邮件发送状态', 'system_mail_send_status', 1, '系统 - 邮件发送状态', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010108, '菜单类型', 'system_menu_type', 1, '系统 - 菜单类型', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010109, '通知类型', 'system_notice_type', 1, '系统 - 通知类型', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010110, '通知渠道', 'system_notification_channel', 1, '系统 - 通知渠道', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010111, 'OAuth2 授权类型', 'system_oauth2_grant_type', 1, '系统 - OAuth2 授权类型', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010112, '内置类型', 'common_builtin_type', 1, '通用 - 内置类型', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010113, '短信渠道编码', 'system_sms_channel_code', 1, '系统 - 短信渠道编码', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010114, '短信接收状态', 'system_sms_receive_status', 1, '系统 - 短信接收状态', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010115, '短信发送状态', 'system_sms_send_status', 1, '系统 - 短信发送状态', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010116, '短信模板类型', 'system_sms_template_type', 1, '系统 - 短信模板类型', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010117, '社交平台类型', 'system_social_type', 1, '系统 - 社交平台类型', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010118, '公告类别', 'system_announcement_category', 1, '系统 - 公告类别', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010119, '公告状态', 'system_announcement_status', 1, '系统 - 公告状态', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010120, '推送目标类型', 'system_push_target_type', 1, '系统 - 通知推送目标类型', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010121, '推送状态', 'system_notice_push_status', 1, '系统 - 通知推送状态', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000010122, '权限操作类型', 'common_permission_type', 1, '通用 - 权限操作类型', 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020001, 1, '是', 'true', 'infra_boolean_string', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020002, 2, '否', 'false', 'infra_boolean_string', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020003, 1, '系统内置', '1', 'infra_config_type', 1, 'danger', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020004, 2, '自定义', '2', 'infra_config_type', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020005, 1, '主库', '1', 'infra_data_source_type', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020006, 2, '从库', '2', 'infra_data_source_type', 1, 'warning', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020007, 3, '备份库', '3', 'infra_data_source_type', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020008, 1, '健康', '0', 'infra_data_source_health_status', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020009, 2, '警告', '1', 'infra_data_source_health_status', 1, 'warning', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020010, 3, '故障', '2', 'infra_data_source_health_status', 1, 'danger', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020011, 1, '轮询', 'round_robin', 'infra_load_balancer_strategy', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020012, 2, '随机', 'random', 'infra_load_balancer_strategy', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020013, 3, '加权', 'weighted', 'infra_load_balancer_strategy', 1, 'warning', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020014, 4, '最小连接数', 'least_connections', 'infra_load_balancer_strategy', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020015, 1, '数据库', '1', 'infra_file_storage', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020016, 2, '本地磁盘', '10', 'infra_file_storage', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020017, 3, 'FTP 服务器', '11', 'infra_file_storage', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020018, 4, 'SFTP 服务器', '12', 'infra_file_storage', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020019, 5, 'S3 对象存储', '20', 'infra_file_storage', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020020, 1, '运行中', '0', 'infra_job_log_status', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020021, 2, '成功', '1', 'infra_job_log_status', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020022, 3, '失败', '2', 'infra_job_log_status', 1, 'danger', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020023, 1, '初始化中', '0', 'infra_job_status', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020024, 2, '开启', '1', 'infra_job_status', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020025, 3, '暂停', '2', 'infra_job_status', 1, 'danger', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020026, 1, '消费中', '0', 'infra_mq_log_status', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020027, 2, '消费成功', '1', 'infra_mq_log_status', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020028, 3, '消费失败', '2', 'infra_mq_log_status', 1, 'danger', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020029, 1, '其它', '0', 'infra_operate_type', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020030, 2, '查询', '1', 'infra_operate_type', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020031, 3, '新增', '2', 'infra_operate_type', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020032, 4, '修改', '3', 'infra_operate_type', 1, 'warning', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020033, 5, '删除', '4', 'infra_operate_type', 1, 'danger', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020034, 6, '导出', '5', 'infra_operate_type', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020035, 7, '导入', '6', 'infra_operate_type', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020036, 1, '会员', '1', 'user_type', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020037, 2, '管理员', '2', 'user_type', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020038, 3, '客户端', '3', 'user_type', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020039, 1, '开启', '1', 'common_status', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020040, 2, '关闭', '0', 'common_status', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020041, 1, '未知', '0', 'system_user_sex', 1, '', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020042, 2, '男', '1', 'system_user_sex', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020043, 3, '女', '2', 'system_user_sex', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020044, 1, '全部数据权限', '1', 'system_data_scope', 1, '', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020045, 2, '指定部门数据权限', '2', 'system_data_scope', 1, '', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020046, 3, '部门数据权限', '3', 'system_data_scope', 1, '', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020047, 4, '部门及以下数据权限', '4', 'system_data_scope', 1, '', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020048, 5, '仅本人数据权限', '5', 'system_data_scope', 1, '', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020049, 1, '使用账号登录', '1', 'system_login_type', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020050, 2, '使用社交登录', '2', 'system_login_type', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020051, 3, '使用手机登陆', '3', 'system_login_type', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020052, 4, '使用短信登陆', '4', 'system_login_type', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020053, 5, '自己主动登出', '20', 'system_login_type', 1, 'warning', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020054, 6, '强制退出', '21', 'system_login_type', 1, 'danger', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020055, 1, '成功', '0', 'system_login_result', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020056, 2, '账号或密码不正确', '10', 'system_login_result', 1, 'danger', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020057, 3, '用户被禁用', '20', 'system_login_result', 1, 'warning', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020058, 4, '验证码不存在', '30', 'system_login_result', 1, 'danger', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020059, 5, '验证码不正确', '31', 'system_login_result', 1, 'danger', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020060, 6, '未知异常', '100', 'system_login_result', 1, 'danger', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020061, 1, '初始化', '0', 'system_mail_send_status', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020062, 2, '发送成功', '10', 'system_mail_send_status', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020063, 3, '发送失败', '20', 'system_mail_send_status', 1, 'danger', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020064, 4, '忽略，即不发送', '30', 'system_mail_send_status', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020065, 1, '目录', '1', 'system_menu_type', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020066, 2, '菜单', '2', 'system_menu_type', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020067, 3, '按钮', '3', 'system_menu_type', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020068, 4, '数据', '4', 'system_menu_type', 1, 'warning', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020069, 1, '系统通知', '1', 'system_notice_type', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020070, 2, '用户通知', '2', 'system_notice_type', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020071, 3, '任务通知', '3', 'system_notice_type', 1, 'warning', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020072, 4, '消息通知', '4', 'system_notice_type', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020073, 5, '警告通知', '5', 'system_notice_type', 1, 'danger', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020074, 1, '站内信', 'INTERNAL', 'system_notification_channel', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020075, 2, '短信', 'SMS', 'system_notification_channel', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020076, 3, '邮件', 'MAIL', 'system_notification_channel', 1, 'warning', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020077, 1, '密码模式', 'password', 'system_oauth2_grant_type', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020078, 2, '授权码模式', 'authorization_code', 'system_oauth2_grant_type', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020079, 3, '简化模式', 'implicit', 'system_oauth2_grant_type', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020080, 4, '客户端模式', 'client_credentials', 'system_oauth2_grant_type', 1, 'warning', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020081, 5, '刷新模式', 'refresh_token', 'system_oauth2_grant_type', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020082, 1, '内置', '1', 'common_builtin_type', 1, 'danger', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020083, 2, '自定义', '2', 'common_builtin_type', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020084, 1, '调试(钉钉)', 'DEBUG_DING_TALK', 'system_sms_channel_code', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020085, 2, '阿里云', 'ALIYUN', 'system_sms_channel_code', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020086, 3, '腾讯云', 'TENCENT', 'system_sms_channel_code', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020087, 4, '华为云', 'HUAWEI', 'system_sms_channel_code', 1, 'warning', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020088, 5, '七牛云', 'QINIU', 'system_sms_channel_code', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020089, 1, '初始化', '0', 'system_sms_receive_status', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020090, 2, '接收成功', '10', 'system_sms_receive_status', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020091, 3, '接收失败', '20', 'system_sms_receive_status', 1, 'danger', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020092, 1, '初始化', '0', 'system_sms_send_status', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020093, 2, '发送成功', '10', 'system_sms_send_status', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020094, 3, '发送失败', '20', 'system_sms_send_status', 1, 'danger', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020095, 4, '忽略，即不发送', '30', 'system_sms_send_status', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020096, 1, '验证码', '1', 'system_sms_template_type', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020097, 2, '通知', '2', 'system_sms_template_type', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020098, 3, '营销', '3', 'system_sms_template_type', 1, 'warning', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020099, 1, '支付宝', '10', 'system_social_type', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020100, 2, '钉钉', '20', 'system_social_type', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020101, 3, '企业微信', '30', 'system_social_type', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020102, 4, '微信公众号', '31', 'system_social_type', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020103, 5, '微信开放平台', '32', 'system_social_type', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020104, 6, '微信小程序', '33', 'system_social_type', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020105, 7, '企业微信(V2)', '34', 'system_social_type', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020106, 1, '系统维护通知', '1', 'system_announcement_category', 1, 'danger', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020107, 2, '新功能发布', '2', 'system_announcement_category', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020108, 3, '重要政策变更', '3', 'system_announcement_category', 1, 'warning', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020109, 1, '草稿', '0', 'system_announcement_status', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020110, 2, '待发布', '1', 'system_announcement_status', 1, 'warning', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020111, 3, '已发布', '2', 'system_announcement_status', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020112, 4, '已过期', '3', 'system_announcement_status', 1, 'danger', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020113, 1, '按用户', '1', 'system_push_target_type', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020114, 2, '按部门', '2', 'system_push_target_type', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020115, 3, '混合', '3', 'system_push_target_type', 1, 'warning', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020116, 1, '推送中', '0', 'system_notice_push_status', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020117, 2, '全部成功', '1', 'system_notice_push_status', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020118, 3, '部分失败', '2', 'system_notice_push_status', 1, 'warning', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020119, 4, '全部失败', '3', 'system_notice_push_status', 1, 'danger', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020120, 1, '未处理', '0', 'infra_api_error_log_process_status', 1, 'warning', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020121, 2, '已处理', '1', 'infra_api_error_log_process_status', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020122, 3, '已忽略', '2', 'infra_api_error_log_process_status', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020123, 1, '基础 CRUD', '1', 'infra_codegen_template_type', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020124, 2, '树形 CRUD', '2', 'infra_codegen_template_type', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020125, 3, '主子表 CRUD', '15', 'infra_codegen_template_type', 1, 'warning', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020126, 1, 'Vue3 Vben5 Element Plus', '0', 'infra_codegen_front_type', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020127, 2, 'Vue3 Vben5 Ant Design Vue', '1', 'infra_codegen_front_type', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020128, 1, '管理后台', '1', 'infra_codegen_scene', 1, 'primary', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020129, 2, '用户端', '2', 'infra_codegen_scene', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020130, 1, '系统', 'system', 'infra_config_module', 1, 'primary', '系统核心配置（应用/日志/安全等）', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020131, 2, '基础设施', 'infra', 'infra_config_module', 1, 'success', '基础设施配置（存储/任务/消息队列等）', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020132, 3, '框架', 'framework', 'infra_config_module', 1, 'warning', '框架层配置（验证码/Excel/IP等）', 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020133, 4, 'AI', 'ai', 'infra_config_module', 1, 'info', 'AI 模块配置（模型/对话/安全等）', 'admin', NOW(), 'admin', NOW(), b'0');

INSERT IGNORE INTO `system_dict_data` (`id`, `sort`, `label`, `value`, `dict_type`, `status`, `color_type`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10200000020134, 1, '查询', '1', 'common_permission_type', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020135, 2, '列表', '2', 'common_permission_type', 1, 'success', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020136, 3, '新增', '3', 'common_permission_type', 1, 'warning', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020137, 4, '修改', '4', 'common_permission_type', 1, 'warning', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020138, 5, '删除', '5', 'common_permission_type', 1, 'danger', NULL, 'admin', NOW(), 'admin', NOW(), b'0'),
(10200000020139, 6, '导出', '6', 'common_permission_type', 1, 'info', NULL, 'admin', NOW(), 'admin', NOW(), b'0');
