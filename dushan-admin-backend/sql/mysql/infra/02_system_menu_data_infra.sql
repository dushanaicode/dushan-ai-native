-- simple 初始数据适配 Native；只写业务目录，不写外部服务凭据。

SET NAMES utf8mb4;

SET time_zone = '+00:00';

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100001, '基础设施', '', 102000000, 0, '/infra', 'ep:monitor', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'group', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100101, '配置管理', '', 102010000, 10000000100001, 'config', 'ep:setting', 'infra/config/index', 'InfraConfig', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100112, '分类查询', 'infra:config:type:query', 102010101, 10000000100101, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100113, '分类新增', 'infra:config:type:create', 102010102, 10000000100101, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100114, '分类修改', 'infra:config:type:update', 102010103, 10000000100101, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100115, '分类删除', 'infra:config:type:delete', 102010104, 10000000100101, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100116, '分类导出', 'infra:config:type:export', 102010105, 10000000100101, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100122, '数据查询', 'infra:config-data:query', 102010201, 10000000100101, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100123, '数据新增', 'infra:config-data:create', 102010202, 10000000100101, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100124, '数据修改', 'infra:config-data:update', 102010203, 10000000100101, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100125, '数据删除', 'infra:config-data:delete', 102010204, 10000000100101, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100126, '数据导出', 'infra:config-data:export', 102010205, 10000000100101, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100201, '文件管理', '', 102020000, 10000000100001, 'file', 'ep:folder', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'group', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100211, '文件列表', '', 102020100, 10000000100201, 'list', 'ep:document', 'infra/file/index', 'InfraFile', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100212, '文件查询', 'infra:file:query', 102020101, 10000000100211, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100213, '文件上传', 'infra:file:upload', 102020102, 10000000100211, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100214, '文件删除', 'infra:file:delete', 102020103, 10000000100211, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100221, '存储配置', '', 102020200, 10000000100201, 'config', 'ep:setting', 'infra/fileConfig/index', 'InfraFileConfig', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100222, '配置查询', 'infra:file:config:query', 102020201, 10000000100221, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100223, '配置新增', 'infra:file:config:create', 102020202, 10000000100221, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100224, '配置修改', 'infra:file:config:update', 102020203, 10000000100221, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100225, '配置删除', 'infra:file:config:delete', 102020204, 10000000100221, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100301, '定时任务', '', 102030000, 10000000100001, 'job', 'ep:alarm-clock', 'infra/job/index', 'InfraJob', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100312, '任务查询', 'infra:job:query', 102030101, 10000000100301, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100313, '任务新增', 'infra:job:create', 102030102, 10000000100301, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100314, '任务修改', 'infra:job:update', 102030103, 10000000100301, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100315, '任务删除', 'infra:job:delete', 102030104, 10000000100301, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100316, '任务触发', 'infra:job:trigger', 102030105, 10000000100301, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100317, '任务导出', 'infra:job:export', 102030106, 10000000100301, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100401, '消息队列', '', 102040000, 10000000100001, 'mq', 'ep:promotion', 'infra/mq/index', 'InfraMq', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100412, '消息查询', 'infra:mq:query', 102040101, 10000000100401, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100413, '消息新增', 'infra:mq:create', 102040102, 10000000100401, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100414, '消息修改', 'infra:mq:update', 102040103, 10000000100401, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100415, '消息删除', 'infra:mq:delete', 102040104, 10000000100401, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100416, '消息导出', 'infra:mq:export', 102040105, 10000000100401, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100417, '消息日志导出', 'infra:mq:log:export', 102040106, 10000000100401, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100418, '消息日志查询', 'infra:mq:log:query', 102040107, 10000000100401, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100501, '数据源配置', '', 102050000, 10000000100001, 'dataSourceConfig', 'ep:coin', 'infra/dataSourceConfig/index', 'InfraDataSourceConfig', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100502, '数据源查询', 'infra:data-source:query', 102050001, 10000000100501, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100503, '数据源新增', 'infra:data-source:create', 102050002, 10000000100501, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100504, '数据源修改', 'infra:data-source:update', 102050003, 10000000100501, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100505, '数据源删除', 'infra:data-source:delete', 102050004, 10000000100501, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100506, '数据源导出', 'infra:data-source:export', 102050005, 10000000100501, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100601, 'API 日志', '', 102060000, 10000000100001, 'api-log', 'ep:document-copy', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'group', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100611, '访问日志', '', 102060100, 10000000100601, 'access', 'ep:tickets', 'infra/apiAccessLog/index', 'InfraApiAccessLog', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100612, '日志查询', 'infra:logger:api-access-log:query', 102060101, 10000000100611, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100613, '日志导出', 'infra:logger:api-access-log:export', 102060102, 10000000100611, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100621, '错误日志', '', 102060200, 10000000100601, 'error', 'ep:warning', 'infra/apiErrorLog/index', 'InfraApiErrorLog', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100622, '日志查询', 'infra:logger:api-error-log:query', 102060201, 10000000100621, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100623, '日志处理', 'infra:logger:api-error-log:update-status', 102060202, 10000000100621, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100624, '日志导出', 'infra:logger:api-error-log:export', 102060203, 10000000100621, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100701, '系统监控', '', 102070000, 10000000100001, 'monitor', 'ep:data-analysis', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'group', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100711, '服务监控', '', 102070100, 10000000100701, 'server', 'ep:monitor', 'infra/server/index', 'InfraServer', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100712, '监控查询', 'infra:server:list', 102070101, 10000000100711, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100721, 'Redis 监控', '', 102070200, 10000000100701, 'redis-monitor', 'ep:data-line', 'infra/redis-monitor/index', 'InfraRedisMonitor', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100722, '监控查询', 'infra:cache:get-monitor-info', 102070201, 10000000100721, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100731, 'Redis 缓存', '', 102070300, 10000000100701, 'redis-cache', 'ep:coin', 'infra/redis-cache/index', 'InfraRedisCache', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100732, '缓存查询', 'infra:cache:get-names', 102070301, 10000000100731, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100741, '在线用户', '', 102070400, 10000000100701, 'online', 'ep:user', 'infra/online/index', 'InfraOnline', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100742, '用户查询', 'infra:online:list', 102070401, 10000000100741, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100743, '强制下线', 'infra:online:force-logout', 102070402, 10000000100741, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100801, 'WebSocket', '', 102080000, 10000000100001, 'webSocket', 'ep:connection', 'infra/webSocket/index', 'InfraWebSocket', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100802, 'WS 查询', 'infra:websocket:query', 102080001, 10000000100801, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100901, '代码生成', '', 102090000, 10000000100001, 'codegen', 'ep:cpu', 'infra/codegen/index', 'InfraCodegen', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000100902, '生成查询', 'infra:codegen:query', 102090001, 10000000100901, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100903, '生成新增', 'infra:codegen:create', 102090002, 10000000100901, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100904, '生成修改', 'infra:codegen:update', 102090003, 10000000100901, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100905, '生成删除', 'infra:codegen:delete', 102090004, 10000000100901, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100906, '代码下载', 'infra:codegen:download', 102090005, 10000000100901, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL),
(10000000100907, '代码预览', 'infra:codegen:preview', 102090006, 10000000100901, '', '', '', '', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'action', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000101001, 'API 文档', '', 102100000, 10000000100001, 'docs', 'ep:document-checked', 'infra/docs/index', 'InfraDocs', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000101101, '监控面板', '', 102110000, 10000000100001, 'monitor-dashboard', 'ep:odometer', 'infra/monitor/index', 'InfraMonitor', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);

INSERT IGNORE INTO `system_menu` (`id`, `name`, `permission`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`, `kind`, `data_permission`, `url`) VALUES
(10000000101201, '表单构建', 'infra:build:list', 102120000, 10000000100001, 'build', 'fa:wpforms', 'infra/build/index', 'InfraBuild', 1, 1, 1, 1, 'system', NOW(), 'system', NOW(), 0, 'page', 0, NULL);
