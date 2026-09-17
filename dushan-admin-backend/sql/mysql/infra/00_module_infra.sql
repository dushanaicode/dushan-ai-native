-- module_infra 建表脚本
-- 数据库方言：mysql
-- 本文件由模型导出生成，请勿手工修改；表结构变更请改模型后重新导出。


-- infra_api_access_log：API 访问日志表
CREATE TABLE infra_api_access_log (
	trace_id VARCHAR(64) NOT NULL COMMENT '链路追踪编号',
	user_id BIGINT COMMENT '用户编号',
	user_type SMALLINT NOT NULL COMMENT '用户类型（枚举）【UserTypeEnum】',
	application_name VARCHAR(100) NOT NULL COMMENT '应用名',
	request_method VARCHAR(10) NOT NULL COMMENT '请求方法名',
	request_url VARCHAR(255) NOT NULL COMMENT '访问地址',
	request_params JSON COMMENT '请求参数 (JSON格式)',
	response_body JSON COMMENT '响应结果 (JSON格式)',
	user_ip VARCHAR(50) NOT NULL COMMENT '用户 IP',
	user_agent VARCHAR(200) NOT NULL COMMENT '浏览器 UA',
	operate_module VARCHAR(100) NOT NULL COMMENT '操作模块',
	operate_name VARCHAR(100) NOT NULL COMMENT '操作名',
	operate_type INTEGER NOT NULL COMMENT '操作分类（枚举类型）【OperateTypeEnum】',
	begin_time DATETIME NOT NULL COMMENT '开始请求时间',
	end_time DATETIME NOT NULL COMMENT '结束请求时间',
	duration INTEGER NOT NULL COMMENT '执行时长，单位：毫秒',
	result_code INTEGER NOT NULL COMMENT '结果码',
	result_msg VARCHAR(512) NOT NULL COMMENT '结果提示',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)ENGINE=InnoDB CHARSET=utf8mb4 COMMENT='API 访问日志表' COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_infra_api_access_log_tenant ON infra_api_access_log (tenant_id);


-- infra_api_error_log：API 错误日志表
CREATE TABLE infra_api_error_log (
	trace_id VARCHAR(64) NOT NULL COMMENT '链路追踪编号',
	user_id BIGINT COMMENT '用户编号',
	user_type SMALLINT NOT NULL COMMENT '用户类型（枚举）【UserTypeEnum】',
	application_name VARCHAR(100) NOT NULL COMMENT '应用名',
	request_method VARCHAR(10) NOT NULL COMMENT '请求方法名',
	request_url VARCHAR(255) NOT NULL COMMENT '访问地址',
	request_params JSON COMMENT '请求参数 (JSON格式)',
	user_ip VARCHAR(50) NOT NULL COMMENT '用户 IP',
	user_agent VARCHAR(200) NOT NULL COMMENT '浏览器 UA',
	exception_time DATETIME NOT NULL COMMENT '异常发生时间',
	exception_name VARCHAR(100) NOT NULL COMMENT '异常名',
	exception_message VARCHAR(512) NOT NULL COMMENT '异常导致的消息',
	exception_root_cause_message VARCHAR(512) NOT NULL COMMENT '异常导致的根消息',
	exception_stack_trace TEXT NOT NULL COMMENT '异常的栈轨迹',
	exception_class_name VARCHAR(255) NOT NULL COMMENT '异常发生的类全名',
	exception_file_name VARCHAR(255) NOT NULL COMMENT '异常发生的类文件',
	exception_method_name VARCHAR(255) NOT NULL COMMENT '异常发生的方法名',
	exception_line_number BIGINT NOT NULL COMMENT '异常发生的方法所在行',
	process_status SMALLINT NOT NULL COMMENT '处理状态',
	process_time DATETIME COMMENT '处理时间',
	process_user_id BIGINT COMMENT '处理用户编号',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)ENGINE=InnoDB CHARSET=utf8mb4 COMMENT='API 错误日志表' COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_infra_api_error_log_tenant ON infra_api_error_log (tenant_id);


-- infra_codegen_table：代码生成-表定义
CREATE TABLE infra_codegen_table (
	data_source_config_id BIGINT NOT NULL COMMENT '数据源配置编号',
	table_name VARCHAR(200) NOT NULL COMMENT '表名称',
	table_comment VARCHAR(500) NOT NULL COMMENT '表描述',
	class_name VARCHAR(200) NOT NULL COMMENT '实体类名称',
	author VARCHAR(100) COMMENT '作者',
	remark VARCHAR(500) COMMENT '备注',
	template_type SMALLINT NOT NULL COMMENT '模板类型: 1=CRUD, 2=Tree, 15=主子表',
	front_type SMALLINT NOT NULL COMMENT '前端类型',
	scene SMALLINT NOT NULL COMMENT '生成场景',
	parent_menu_id BIGINT COMMENT '父菜单编号',
	module_name VARCHAR(100) NOT NULL COMMENT '模块名，如 system、infra',
	business_name VARCHAR(100) NOT NULL COMMENT '业务名，如 user、dict',
	class_comment VARCHAR(200) NOT NULL COMMENT '类描述，如 用户',
	enable_export BOOL NOT NULL COMMENT '是否启用导出',
	tree_parent_column_id BIGINT COMMENT '树表-父字段编号',
	tree_name_column_id BIGINT COMMENT '树表-名称字段编号',
	master_table_id BIGINT COMMENT '主子表-主表编号',
	sub_join_column_id BIGINT COMMENT '主子表-子表关联字段编号',
	sub_join_many BOOL COMMENT '主子表-关联关系: true=一对多, false=一对一',
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN deleted = 0 THEN 1 ELSE NULL END) COMMENT '仅有效记录参与业务唯一约束',
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_infra_codegen_table_active_0 UNIQUE (data_source_config_id, table_name, active_key)
)ENGINE=InnoDB CHARSET=utf8mb4 COMMENT='代码生成-表定义' COLLATE utf8mb4_unicode_ci;


-- infra_config_type：配置类型表
CREATE TABLE infra_config_type (
	module VARCHAR(50) NOT NULL COMMENT '所属模块标识',
	name VARCHAR(100) NOT NULL COMMENT '配置类型名称',
	code VARCHAR(100) NOT NULL COMMENT '配置类型编码',
	status SMALLINT NOT NULL COMMENT '状态（1-启用，0-禁用）',
	remark VARCHAR(500) COMMENT '备注',
	deleted_time DATETIME COMMENT '删除时间',
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN deleted = 0 THEN 1 ELSE NULL END) COMMENT '仅有效记录参与业务唯一约束',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_infra_config_type_tenant_id UNIQUE (tenant_id, id),
	CONSTRAINT uq_infra_config_type_active_0 UNIQUE (tenant_id, code, active_key)
)ENGINE=InnoDB CHARSET=utf8mb4 COMMENT='配置类型表' COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_infra_config_type_tenant ON infra_config_type (tenant_id);


-- infra_data_source_config：数据源配置表
CREATE TABLE infra_data_source_config (
	name VARCHAR(100) NOT NULL COMMENT '数据源名称',
	url VARCHAR(500) NOT NULL COMMENT '数据源连接URL',
	status SMALLINT NOT NULL COMMENT '状态：1-启用，0-禁用',
	db_type VARCHAR(50) NOT NULL COMMENT '数据库类型',
	source_type SMALLINT NOT NULL COMMENT '数据源类型：1-主库，2-从库',
	is_default BOOL NOT NULL COMMENT '是否默认数据源',
	pool_size SMALLINT NOT NULL COMMENT '连接池大小',
	max_overflow SMALLINT NOT NULL COMMENT '最大溢出连接数',
	pool_recycle SMALLINT NOT NULL COMMENT '连接最大复用时间（秒）',
	pool_timeout SMALLINT NOT NULL COMMENT '获取连接最大等待时间（秒）',
	echo BOOL NOT NULL COMMENT '是否开启SQL日志',
	remark VARCHAR(500) COMMENT '备注',
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN deleted = 0 THEN 1 ELSE NULL END) COMMENT '仅有效记录参与业务唯一约束',
	default_active SMALLINT GENERATED ALWAYS AS (CASE WHEN deleted = 0 AND is_default = 1 THEN 1 ELSE NULL END) COMMENT '有效默认配置唯一标记',
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_infra_data_source_config_default_active UNIQUE (source_type, default_active),
	CONSTRAINT uq_infra_data_source_config_active_0 UNIQUE (name, active_key)
)ENGINE=InnoDB CHARSET=utf8mb4 COMMENT='数据源配置表' COLLATE utf8mb4_unicode_ci;


-- infra_file_config：文件配置表
CREATE TABLE infra_file_config (
	name VARCHAR(100) NOT NULL COMMENT '配置名',
	storage INTEGER NOT NULL COMMENT '存储器（枚举类型）',
	remark TEXT COMMENT '备注',
	status SMALLINT NOT NULL COMMENT '状态（1-启用，0-禁用）',
	master BOOL NOT NULL COMMENT '是否为主配置',
	config JSON NOT NULL COMMENT '文件客户端配置',
	master_active SMALLINT GENERATED ALWAYS AS (CASE WHEN deleted = 0 AND master = 1 THEN 1 ELSE NULL END) COMMENT '有效默认配置唯一标记',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_infra_file_config_master_active UNIQUE (tenant_id, master_active),
	CONSTRAINT uq_infra_file_config_tenant_id UNIQUE (tenant_id, id)
)ENGINE=InnoDB CHARSET=utf8mb4 COMMENT='文件配置表' COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_infra_file_config_tenant ON infra_file_config (tenant_id);


-- infra_job：定时任务 DO
CREATE TABLE infra_job (
	name VARCHAR(255) NOT NULL COMMENT '任务名称',
	status INTEGER NOT NULL COMMENT '任务状态，枚举 【JobStatusEnum】',
	handler_name VARCHAR(255) NOT NULL COMMENT '处理器的名字',
	handler_param VARCHAR(512) COMMENT '处理器的参数',
	cron_expression VARCHAR(255) NOT NULL COMMENT 'CRON 表达式',
	retry_count INTEGER NOT NULL COMMENT '重试次数，如果不重试，则设置为 0',
	retry_interval INTEGER NOT NULL COMMENT '重试间隔，单位：毫秒，如果没有间隔，则设置为 0',
	monitor_timeout INTEGER COMMENT '监控超时时间，单位：毫秒，为空时，表示不监控',
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN deleted = 0 THEN 1 ELSE NULL END) COMMENT '仅有效记录参与业务唯一约束',
	revision VARCHAR(64) NOT NULL COMMENT '计划版本',
	effective_at DATETIME NOT NULL COMMENT '版本生效时间 UTC',
	parameters JSON NOT NULL COMMENT '经过 handler 参数模型验证的值',
	tenant_id VARCHAR(256) COMMENT '任务目标租户；控制面记录不参与行租户过滤',
	fan_out BOOL NOT NULL COMMENT '是否向已授权租户扇出',
	max_instances INTEGER NOT NULL COMMENT '最大并发数',
	timeout_seconds FLOAT NOT NULL COMMENT '单次执行上限',
	retry_backoff FLOAT NOT NULL COMMENT '重试退避倍率',
	stop_after_failure BOOL NOT NULL COMMENT '失败后停止匹配版本',
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_infra_job_active_0 UNIQUE (handler_name, active_key)
)ENGINE=InnoDB CHARSET=utf8mb4 COMMENT='定时任务 DO' COLLATE utf8mb4_unicode_ci;


-- infra_job_log：定时任务的执行日志
CREATE TABLE infra_job_log (
	job_id BIGINT NOT NULL COMMENT '任务编号，关联 JobDO.id',
	handler_name VARCHAR(255) NOT NULL COMMENT '处理器的名字，冗余字段 JobDO.handler_name',
	handler_param VARCHAR(512) COMMENT '处理器的参数，冗余字段 JobDO.handler_param',
	execute_index INTEGER NOT NULL COMMENT '第几次执行，用于区分是不是重试执行。如果是重试执行，则 index 大于 1',
	begin_time DATETIME COMMENT '开始执行时间',
	end_time DATETIME COMMENT '结束执行时间',
	duration INTEGER COMMENT '执行时长，单位：毫秒',
	status INTEGER NOT NULL COMMENT '状态，枚举 【JobLogStatusEnum】',
	result VARCHAR(4096) COMMENT '结果数据，成功时是执行结果，失败时是异常堆栈',
	request_id VARCHAR(128) NOT NULL COMMENT '持久执行请求编号',
	state VARCHAR(32) NOT NULL COMMENT 'Native 执行终态',
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)ENGINE=InnoDB CHARSET=utf8mb4 COMMENT='定时任务的执行日志' COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_infra_job_log_request_id ON infra_job_log (request_id);


-- infra_job_request：调度器持久协调记录
CREATE TABLE infra_job_request (
	request_id VARCHAR(128) NOT NULL COMMENT '跨进程幂等请求编号',
	job_id BIGINT NOT NULL COMMENT '任务编号',
	request JSON NOT NULL COMMENT 'Native JobRequest 快照',
	state VARCHAR(32) NOT NULL COMMENT 'pending/claimed/执行终态',
	owner VARCHAR(128) COMMENT '独占调度 owner',
	ready_at DATETIME NOT NULL COMMENT '允许领取时间 UTC',
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (request_id)
)ENGINE=InnoDB CHARSET=utf8mb4 COMMENT='调度器持久协调记录' COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_infra_job_request_job_id ON infra_job_request (job_id);
CREATE INDEX ix_infra_job_request_ready_at ON infra_job_request (ready_at);
CREATE INDEX ix_infra_job_request_state ON infra_job_request (state);


-- infra_job_schedule：调度器持久协调记录
CREATE TABLE infra_job_schedule (
	job_id BIGINT NOT NULL COMMENT '任务编号',
	checkpoint DATETIME NOT NULL COMMENT '永久定时投递游标；不随历史请求清理',
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (job_id)
)ENGINE=InnoDB CHARSET=utf8mb4 COMMENT='调度器持久协调记录' COLLATE utf8mb4_unicode_ci;


-- infra_job_signal：调度器持久协调记录
CREATE TABLE infra_job_signal (
	revision BIGINT NOT NULL COMMENT '任务定义提交后的合并通知版本',
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)ENGINE=InnoDB CHARSET=utf8mb4 COMMENT='调度器持久协调记录' COLLATE utf8mb4_unicode_ci;


-- infra_mq：MQ 消息的定义
CREATE TABLE infra_mq (
	topic VARCHAR(255) NOT NULL COMMENT '消息主题 Topic',
	consumer VARCHAR(255) NOT NULL COMMENT '消费者名称，即处理函数名',
	retry_count INTEGER NOT NULL COMMENT '重试次数',
	description VARCHAR(512) COMMENT '描述',
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN deleted = 0 THEN 1 ELSE NULL END) COMMENT '仅有效记录参与业务唯一约束',
	enabled BOOL NOT NULL COMMENT '部署覆盖开关',
	concurrency INTEGER COMMENT '部署覆盖并发数',
	prefetch INTEGER COMMENT '部署覆盖预取数',
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_infra_mq_active_0 UNIQUE (consumer, active_key)
)ENGINE=InnoDB CHARSET=utf8mb4 COMMENT='MQ 消息的定义' COLLATE utf8mb4_unicode_ci;


-- infra_mq_log：MQ 消息的消费日志
CREATE TABLE infra_mq_log (
	message_id VARCHAR(64) NOT NULL COMMENT '消息ID',
	topic VARCHAR(255) NOT NULL COMMENT '消息主题',
	consumer VARCHAR(255) NOT NULL COMMENT '消费者名称，冗余字段',
	execute_index INTEGER NOT NULL COMMENT '第几次消费，用于区分是不是重试消费。如果是重试，则 index 大于 1',
	begin_time DATETIME COMMENT '开始消费时间',
	end_time DATETIME COMMENT '结束消费时间',
	duration INTEGER COMMENT '消费时长，单位：毫秒',
	status INTEGER NOT NULL COMMENT '状态，枚举 MqLogStatusEnum',
	result TEXT COMMENT '结果数据，成功时是执行结果，失败时是异常堆栈',
	payload JSON COMMENT '仅留空字段承接历史表结构；不记录正文或身份凭证',
	state VARCHAR(32) NOT NULL COMMENT 'Native 消费终态',
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)ENGINE=InnoDB CHARSET=utf8mb4 COMMENT='MQ 消息的消费日志' COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_infra_mq_log_message_id ON infra_mq_log (message_id);
CREATE INDEX ix_infra_mq_log_topic ON infra_mq_log (topic);


-- infra_codegen_column：代码生成-列定义
CREATE TABLE infra_codegen_column (
	table_id BIGINT NOT NULL COMMENT '表编号',
	column_name VARCHAR(200) NOT NULL COMMENT '字段列名',
	column_comment VARCHAR(500) NOT NULL COMMENT '字段描述',
	data_type VARCHAR(100) NOT NULL COMMENT '字段物理类型',
	column_size BIGINT COMMENT '字段长度',
	field_type VARCHAR(50) NOT NULL COMMENT 'Python字段类型',
	field_name VARCHAR(200) NOT NULL COMMENT 'Python属性名',
	create_operation BOOL NOT NULL COMMENT '是否参与新增操作',
	update_operation BOOL NOT NULL COMMENT '是否参与编辑操作',
	list_operation BOOL NOT NULL COMMENT '是否作为查询条件',
	list_operation_result BOOL NOT NULL COMMENT '是否在列表中展示',
	list_operation_condition VARCHAR(20) NOT NULL COMMENT '查询方式: =, !=, >, >=, <, <=, LIKE, BETWEEN',
	nullable BOOL NOT NULL COMMENT '是否允许为空',
	html_type VARCHAR(50) NOT NULL COMMENT '显示类型: input, textarea, select, radio, checkbox, datetime, imageUpload, fileUpload, editor',
	dict_type VARCHAR(200) COMMENT '关联字典类型',
	example VARCHAR(500) COMMENT '示例值',
	order_no SMALLINT NOT NULL COMMENT '排序',
	primary_key BOOL NOT NULL COMMENT '是否主键',
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN deleted = 0 THEN 1 ELSE NULL END) COMMENT '仅有效记录参与业务唯一约束',
	computed_expression TEXT COMMENT '数据库生成列表达式',
	computed_persisted BOOL COMMENT '生成列是否持久化',
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT fk_infra_codegen_column_table_id FOREIGN KEY(table_id) REFERENCES infra_codegen_table (id),
	CONSTRAINT uq_infra_codegen_column_active_0 UNIQUE (table_id, column_name, active_key)
)ENGINE=InnoDB CHARSET=utf8mb4 COMMENT='代码生成-列定义' COLLATE utf8mb4_unicode_ci;


-- infra_config_data：参数配置表
CREATE TABLE infra_config_data (
	type_id BIGINT NOT NULL COMMENT '配置类型ID',
	name VARCHAR(100) NOT NULL COMMENT '参数名称',
	`key` VARCHAR(100) NOT NULL COMMENT '参数键名',
	value VARCHAR(500) NOT NULL COMMENT '参数键值',
	description VARCHAR(500) COMMENT '配置描述',
	input_type VARCHAR(50) COMMENT 'UI控件类型',
	input_props TEXT COMMENT 'UI控件属性JSON',
	sort INTEGER NOT NULL COMMENT '显示顺序',
	visible INTEGER NOT NULL COMMENT '是否可见',
	remark VARCHAR(500) COMMENT '备注',
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN deleted = 0 THEN 1 ELSE NULL END) COMMENT '仅有效记录参与业务唯一约束',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT fk_infra_config_data_type_id FOREIGN KEY(tenant_id, type_id) REFERENCES infra_config_type (tenant_id, id),
	CONSTRAINT uq_infra_config_data_active_0 UNIQUE (tenant_id, `key`, active_key)
)ENGINE=InnoDB CHARSET=utf8mb4 COMMENT='参数配置表' COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_infra_config_data_tenant ON infra_config_data (tenant_id);


-- infra_file：文件表
CREATE TABLE infra_file (
	config_id BIGINT NOT NULL COMMENT '配置编号',
	name VARCHAR(255) NOT NULL COMMENT '原文件名',
	original_name VARCHAR(255) NOT NULL COMMENT '原始文件名',
	path VARCHAR(255) NOT NULL COMMENT '路径，即文件名',
	storage_path VARCHAR(1000) NOT NULL COMMENT '实际存储路径',
	url VARCHAR(255) NOT NULL COMMENT '访问地址',
	type VARCHAR(255) NOT NULL COMMENT '文件的 MIME 类型',
	size INTEGER NOT NULL COMMENT '文件大小',
	hash VARCHAR(64) COMMENT '文件哈希值',
	file_metadata JSON COMMENT '文件元数据',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT fk_infra_file_config_id FOREIGN KEY(tenant_id, config_id) REFERENCES infra_file_config (tenant_id, id)
)ENGINE=InnoDB CHARSET=utf8mb4 COMMENT='文件表' COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_infra_file_tenant ON infra_file (tenant_id);


-- infra_file_content：文件内容表
CREATE TABLE infra_file_content (
	config_id BIGINT NOT NULL COMMENT '配置编号',
	path VARCHAR(255) NOT NULL COMMENT '路径，即文件名',
	content LONGBLOB NOT NULL COMMENT '文件内容',
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN deleted = 0 THEN 1 ELSE NULL END) COMMENT '仅有效记录参与业务唯一约束',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT fk_infra_file_content_config_id FOREIGN KEY(tenant_id, config_id) REFERENCES infra_file_config (tenant_id, id),
	CONSTRAINT uq_infra_file_content_active_0 UNIQUE (tenant_id, config_id, path, active_key)
)ENGINE=InnoDB CHARSET=utf8mb4 COMMENT='文件内容表' COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_infra_file_content_tenant ON infra_file_content (tenant_id);
