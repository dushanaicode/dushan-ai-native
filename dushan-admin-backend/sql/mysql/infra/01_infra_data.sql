-- simple 初始数据适配 Native；只写业务目录，不写外部服务凭据。

SET NAMES utf8mb4;

SET time_zone = '+00:00';

INSERT IGNORE INTO `infra_config_type` (`id`, `module`, `tenant_id`, `name`, `code`, `status`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10300000010001, 'system', '1', '应用配置', 'APP_SETTINGS', 1, 'AppSettings - 应用基础配置（名称/版本/业务开关）', 'admin', NOW(), 'admin', NOW(), 0),
(10300000010002, 'system', '1', '日期时间配置', 'DATETIME_SETTINGS', 1, 'DateTimeSettings - 时区配置', 'admin', NOW(), 'admin', NOW(), 0),
(10300000010003, 'system', '1', '日志配置', 'LOG_SETTINGS', 1, 'LogSettings - 日志级别/保留策略', 'admin', NOW(), 'admin', NOW(), 0),
(10300000010004, 'system', '1', 'API加解密配置', 'API_ENCRYPT_SETTINGS', 1, 'ApiEncryptSettings - API加解密开关', 'admin', NOW(), 'admin', NOW(), 0),
(10300000010005, 'system', '1', 'XSS配置', 'XSS_SETTINGS', 1, 'XssSettings - XSS过滤开关', 'admin', NOW(), 'admin', NOW(), 0),
(10300000010006, 'system', '1', '验证码配置', 'CAPTCHA_SETTINGS', 1, 'CaptchaSettings - 验证码开关/频率/过期时间', 'admin', NOW(), 'admin', NOW(), 0),
(10300000010007, 'system', '1', 'Excel配置', 'EXCEL_SETTINGS', 1, 'ExcelSettings - 导入导出样式/行数限制', 'admin', NOW(), 'admin', NOW(), 0),
(10300000010008, 'system', '1', 'IP配置', 'IP_SETTINGS', 1, 'IpSettings - IP查询超时/缓存配置', 'admin', NOW(), 'admin', NOW(), 0);

INSERT IGNORE INTO `infra_config_data` (`id`, `type_id`, `tenant_id`, `name`, `key`, `value`, `description`, `input_type`, `input_props`, `sort`, `visible`, `remark`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10300000020001, 10300000010001, '1', '应用名称', 'APP_NAME', 'DUSHAN-SERVER', NULL, NULL, NULL, 10, 1, '应用名称', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020002, 10300000010001, '1', '应用作者', 'APP_AUTHER', '渡山', NULL, NULL, NULL, 20, 1, '应用作者', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020003, 10300000010001, '1', '应用版本号', 'APP_VERSION', '1.0.0', NULL, NULL, NULL, 30, 1, '应用版本号', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020004, 10300000010001, '1', '访问日志', 'APP_ACCESS_LOG_ENABLE', 'true', NULL, NULL, NULL, 40, 1, '是否开启访问日志功能', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020005, 10300000010001, '1', '国际化开关', 'APP_I18N_ENABLED', 'true', NULL, NULL, NULL, 50, 1, '是否启用国际化翻译', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020006, 10300000010001, '1', '默认语言', 'APP_I18N_DEFAULT_LANG', 'zh-CN', NULL, NULL, NULL, 60, 1, '默认语言（zh-CN/en-US）', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020007, 10300000010001, '1', '允许修改系统角色', 'APP_ALLOW_MODIFY_SYSTEM_ROLE', 'true', NULL, NULL, NULL, 70, 1, '是否允许修改系统内置角色', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020009, 10300000010002, '1', '默认时区', 'DATETIME_TIMEZONE', 'Asia/Shanghai', NULL, NULL, NULL, 10, 1, '默认时区', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020010, 10300000010003, '1', '文件日志总开关', 'LOG_ENABLE_FILE_OVERALL', 'true', NULL, NULL, NULL, 10, 1, '是否启用文件日志', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020011, 10300000010003, '1', 'JSON结构化日志', 'LOG_ENABLE_JSON_FORMAT', 'false', NULL, NULL, NULL, 20, 1, '是否启用JSON结构化日志', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020012, 10300000010003, '1', '控制台日志级别', 'LOG_CONSOLE_LEVEL', 'DEBUG', NULL, NULL, NULL, 30, 1, '控制台输出的最低级别', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020013, 10300000010003, '1', '日志轮转大小', 'LOG_ROTATION_SIZE', '20 MB', NULL, NULL, NULL, 40, 1, '日志轮转大小', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020014, 10300000010003, '1', '异步写入', 'LOG_ENQUEUE', 'true', NULL, NULL, NULL, 50, 1, '是否启用异步写入', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020015, 10300000010003, '1', '日志压缩格式', 'LOG_COMPRESSION', 'zip', NULL, NULL, NULL, 60, 1, '日志压缩格式', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020016, 10300000010003, '1', 'Info日志级别', 'LOG_FILE_LEVEL_INFO', 'INFO', NULL, NULL, NULL, 70, 1, 'Info日志文件的最低记录级别', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020017, 10300000010003, '1', 'Info日志保留时间', 'LOG_RETENTION_INFO', '7 days', NULL, NULL, NULL, 80, 1, 'Info日志保留时间', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020018, 10300000010003, '1', 'Warning日志级别', 'LOG_FILE_LEVEL_WARNING', 'WARNING', NULL, NULL, NULL, 90, 1, 'Warning日志文件的最低记录级别', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020019, 10300000010003, '1', 'Warning日志保留时间', 'LOG_RETENTION_WARN', '15 days', NULL, NULL, NULL, 100, 1, 'Warning日志保留时间', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020020, 10300000010003, '1', 'Error日志级别', 'LOG_FILE_LEVEL_ERROR', 'ERROR', NULL, NULL, NULL, 110, 1, 'Error日志文件的最低记录级别', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020021, 10300000010003, '1', 'Error日志保留时间', 'LOG_RETENTION_ERROR', '30 days', NULL, NULL, NULL, 120, 1, 'Error日志保留时间', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020022, 10300000010004, '1', 'API加解密开关', 'API_ENCRYPT_ENABLE', 'false', NULL, NULL, NULL, 10, 1, '是否启用API加解密', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020023, 10300000010005, '1', 'XSS过滤器开关', 'XSS_XSS_FILTER_ENABLED', 'true', NULL, NULL, NULL, 10, 1, '是否启用XSS过滤器', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020024, 10300000010006, '1', '验证码开关', 'CAPTCHA_ENABLE', 'true', NULL, NULL, NULL, 10, 1, '是否开启验证码', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020025, 10300000010006, '1', '验证码过期时间', 'CAPTCHA_TIMING_CLEAR', '180', NULL, NULL, NULL, 20, 1, '验证码过期时间(秒)', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020026, 10300000010006, '1', '频率限制开关', 'CAPTCHA_REQ_FREQUENCY_LIMIT_ENABLE', 'false', NULL, NULL, NULL, 30, 1, '是否启用频率限制', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020027, 10300000010006, '1', '验证失败最大次数', 'CAPTCHA_REQ_GET_LOCK_LIMIT', '5', NULL, NULL, NULL, 40, 1, '验证失败最大次数', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020028, 10300000010006, '1', '锁定时间间隔', 'CAPTCHA_REQ_GET_LOCK_SECONDS', '120', NULL, NULL, NULL, 50, 1, '锁定时间间隔(秒)', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020029, 10300000010006, '1', 'Get接口请求限制', 'CAPTCHA_REQ_GET_MINUTE_LIMIT', '30', NULL, NULL, NULL, 60, 1, 'Get接口一分钟请求数', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020030, 10300000010006, '1', 'Check接口请求限制', 'CAPTCHA_REQ_CHECK_MINUTE_LIMIT', '60', NULL, NULL, NULL, 70, 1, 'Check接口一分钟请求数', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020031, 10300000010007, '1', '表头字体加粗', 'EXCEL_HEADER_FONT_BOLD', 'true', NULL, NULL, NULL, 10, 1, '表头字体是否加粗', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020032, 10300000010007, '1', '表头字体大小', 'EXCEL_HEADER_FONT_SIZE', '11', NULL, NULL, NULL, 20, 1, '表头字体大小', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020033, 10300000010007, '1', '自动调整列宽', 'EXCEL_AUTO_ADJUST_COLUMN_WIDTH', 'true', NULL, NULL, NULL, 30, 1, '是否自动调整列宽', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020034, 10300000010007, '1', '最大列宽', 'EXCEL_MAX_COLUMN_WIDTH', '60', NULL, NULL, NULL, 40, 1, '最大列宽', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020035, 10300000010007, '1', '最小列宽', 'EXCEL_MIN_COLUMN_WIDTH', '10', NULL, NULL, NULL, 50, 1, '最小列宽', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020036, 10300000010007, '1', '只读模式', 'EXCEL_READ_ONLY_MODE', 'true', NULL, NULL, NULL, 60, 1, '读取模式是否只读', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020037, 10300000010007, '1', '数据模式', 'EXCEL_DATA_ONLY_MODE', 'true', NULL, NULL, NULL, 70, 1, '是否只读取数据（不读取公式）', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020038, 10300000010007, '1', '最大导入行数', 'EXCEL_MAX_IMPORT_ROWS', '10000', NULL, NULL, NULL, 80, 1, '最大导入行数', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020039, 10300000010007, '1', '金额小数位数', 'EXCEL_MONEY_DECIMAL_PLACES', '2', NULL, NULL, NULL, 90, 1, '金额小数位数', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020040, 10300000010008, '1', 'IP查询超时时间', 'IP_IP_QUERY_TIMEOUT', '5.0', NULL, NULL, NULL, 10, 1, 'IP查询超时时间(秒)', 'admin', NOW(), 'admin', NOW(), 0),
(10300000020041, 10300000010008, '1', 'IP缓存大小', 'IP_IP_CACHE_SIZE', '1024', NULL, NULL, NULL, 20, 1, 'IP查询结果缓存大小', 'admin', NOW(), 'admin', NOW(), 0);

INSERT IGNORE INTO `infra_file_config` (`id`, `name`, `storage`, `remark`, `status`, `master`, `config`, `tenant_id`, `creator`, `create_time`, `updater`, `update_time`, `deleted`) VALUES
(10300000040001, '数据库', 1, '文件内容存储到数据库 infra_file_content 表，适合小文件和开发环境', 1, 1, '{"domain":"http://localhost:48080"}', '1', '10100000010001', NOW(), '10100000010001', NOW(), 0);

INSERT IGNORE INTO `infra_job` (`id`, `name`, `status`, `handler_name`, `handler_param`, `cron_expression`, `retry_count`, `retry_interval`, `monitor_timeout`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `parameters`, `revision`, `effective_at`, `tenant_id`, `fan_out`, `max_instances`, `timeout_seconds`, `retry_backoff`, `stop_after_failure`) VALUES
(10300000050001, '任务日志清理任务', 1, 'infra.job.log.clean', '{}', '0 2 * * *', 3, 5000, 60000, 'system', NOW(), 'system', NOW(), b'0', '{}', 'seed-1', UTC_TIMESTAMP(), '1', 0, 1, 300, 1, 0),
(10300000050002, '访问日志清理任务', 1, 'infra.log.access.clean', '{}', '30 2 * * *', 3, 5000, 60000, 'system', NOW(), 'system', NOW(), b'0', '{}', 'seed-1', UTC_TIMESTAMP(), '1', 0, 1, 300, 1, 0),
(10300000050003, '错误日志清理任务', 1, 'infra.log.error.clean', '{}', '0 3 * * *', 3, 5000, 60000, 'system', NOW(), 'system', NOW(), b'0', '{}', 'seed-1', UTC_TIMESTAMP(), '1', 0, 1, 300, 1, 0),
(10300000050004, '公告定时任务', 1, 'system.announcement.publish', '{}', '* * * * *', 3, 5000, 120000, 'system', NOW(), 'system', NOW(), b'0', '{}', 'seed-1', UTC_TIMESTAMP(), '1', 0, 1, 300, 1, 0),
(10300000050005, '数据权限同步任务', 1, 'system.permission.sync', '{}', '0 4 * * *', 3, 5000, 60000, 'system', NOW(), 'system', NOW(), b'0', '{}', 'seed-1', UTC_TIMESTAMP(), '1', 0, 1, 300, 1, 0),
(10300000050006, '数据库主从延迟检查任务', 1, 'infra.database.health', '{}', '0 5 * * *', 3, 5000, 60000, 'system', NOW(), 'system', NOW(), b'0', '{}', 'seed-1', UTC_TIMESTAMP(), '1', 0, 1, 300, 1, 0),
(10300000050007, '数据库备份任务', 2, 'infra.database.backup', '{}', '0 2 * * *', 1, 300000, 1800000, 'system', NOW(), 'system', NOW(), b'0', '{}', 'seed-1', UTC_TIMESTAMP(), '1', 0, 1, 300, 1, 0),
(10300000050008, '数据库指标采集任务', 1, 'infra.database.metrics', '{}', '*/5 * * * *', 0, 0, 30000, 'system', NOW(), 'system', NOW(), b'0', '{}', 'seed-1', UTC_TIMESTAMP(), '1', 0, 1, 300, 1, 0);

INSERT IGNORE INTO infra_job_signal (id,revision,creator,updater,create_time,update_time,deleted) VALUES (1,0,'','',UTC_TIMESTAMP(),UTC_TIMESTAMP(),0);
