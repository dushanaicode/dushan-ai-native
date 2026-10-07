-- module_infra 建表脚本
-- 数据库方言：dm
-- 本文件由模型导出生成，请勿手工修改；表结构变更请改模型后重新导出。


-- infra_api_access_log：API 访问日志表
CREATE TABLE infra_api_access_log (
	trace_id VARCHAR2(64 CHAR) NOT NULL, 
	user_id BIGINT, 
	user_type SMALLINT NOT NULL, 
	application_name VARCHAR2(100 CHAR) NOT NULL, 
	request_method VARCHAR2(10 CHAR) NOT NULL, 
	request_url VARCHAR2(255 CHAR) NOT NULL, 
	request_params JSON, 
	response_body JSON, 
	user_ip VARCHAR2(50 CHAR) NOT NULL, 
	user_agent VARCHAR2(200 CHAR) NOT NULL, 
	operate_module VARCHAR2(100 CHAR) NOT NULL, 
	operate_name VARCHAR2(100 CHAR) NOT NULL, 
	operate_type INTEGER NOT NULL, 
	begin_time DATETIME NOT NULL, 
	end_time DATETIME NOT NULL, 
	duration INTEGER NOT NULL, 
	result_code INTEGER NOT NULL, 
	result_msg VARCHAR2(512 CHAR) NOT NULL, 
	tenant_id VARCHAR2(32 CHAR) NOT NULL, 
	id BIGINT NOT NULL IDENTITY(1, 1), 
	creator VARCHAR2(64 CHAR) NOT NULL, 
	create_time DATETIME NOT NULL, 
	updater VARCHAR2(64 CHAR) NOT NULL, 
	update_time DATETIME NOT NULL, 
	deleted SMALLINT NOT NULL, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_infra_api_access_log_tenant ON infra_api_access_log (tenant_id);
COMMENT ON TABLE infra_api_access_log IS 'API 访问日志表';
COMMENT ON COLUMN infra_api_access_log.trace_id IS '链路追踪编号';
COMMENT ON COLUMN infra_api_access_log.user_id IS '用户编号';
COMMENT ON COLUMN infra_api_access_log.user_type IS '用户类型（枚举）【UserTypeEnum】';
COMMENT ON COLUMN infra_api_access_log.application_name IS '应用名';
COMMENT ON COLUMN infra_api_access_log.request_method IS '请求方法名';
COMMENT ON COLUMN infra_api_access_log.request_url IS '访问地址';
COMMENT ON COLUMN infra_api_access_log.request_params IS '请求参数 (JSON格式)';
COMMENT ON COLUMN infra_api_access_log.response_body IS '响应结果 (JSON格式)';
COMMENT ON COLUMN infra_api_access_log.user_ip IS '用户 IP';
COMMENT ON COLUMN infra_api_access_log.user_agent IS '浏览器 UA';
COMMENT ON COLUMN infra_api_access_log.operate_module IS '操作模块';
COMMENT ON COLUMN infra_api_access_log.operate_name IS '操作名';
COMMENT ON COLUMN infra_api_access_log.operate_type IS '操作分类（枚举类型）【OperateTypeEnum】';
COMMENT ON COLUMN infra_api_access_log.begin_time IS '开始请求时间';
COMMENT ON COLUMN infra_api_access_log.end_time IS '结束请求时间';
COMMENT ON COLUMN infra_api_access_log.duration IS '执行时长，单位：毫秒';
COMMENT ON COLUMN infra_api_access_log.result_code IS '结果码';
COMMENT ON COLUMN infra_api_access_log.result_msg IS '结果提示';
COMMENT ON COLUMN infra_api_access_log.tenant_id IS '租户 ID（租户主键的字符串形式）';
COMMENT ON COLUMN infra_api_access_log.id IS '主键 ID';
COMMENT ON COLUMN infra_api_access_log.creator IS '创建者账号 ID';
COMMENT ON COLUMN infra_api_access_log.create_time IS '创建时间（UTC）';
COMMENT ON COLUMN infra_api_access_log.updater IS '更新者账号 ID';
COMMENT ON COLUMN infra_api_access_log.update_time IS '更新时间（UTC）';
COMMENT ON COLUMN infra_api_access_log.deleted IS '是否已删除';


-- infra_api_error_log：API 错误日志表
CREATE TABLE infra_api_error_log (
	trace_id VARCHAR2(64 CHAR) NOT NULL, 
	user_id BIGINT, 
	user_type SMALLINT NOT NULL, 
	application_name VARCHAR2(100 CHAR) NOT NULL, 
	request_method VARCHAR2(10 CHAR) NOT NULL, 
	request_url VARCHAR2(255 CHAR) NOT NULL, 
	request_params JSON, 
	user_ip VARCHAR2(50 CHAR) NOT NULL, 
	user_agent VARCHAR2(200 CHAR) NOT NULL, 
	exception_time DATETIME NOT NULL, 
	exception_name VARCHAR2(100 CHAR) NOT NULL, 
	exception_message VARCHAR2(512 CHAR) NOT NULL, 
	exception_root_cause_message VARCHAR2(512 CHAR) NOT NULL, 
	exception_stack_trace TEXT NOT NULL, 
	exception_class_name VARCHAR2(255 CHAR) NOT NULL, 
	exception_file_name VARCHAR2(255 CHAR) NOT NULL, 
	exception_method_name VARCHAR2(255 CHAR) NOT NULL, 
	exception_line_number BIGINT NOT NULL, 
	process_status SMALLINT NOT NULL, 
	process_time DATETIME, 
	process_user_id BIGINT, 
	tenant_id VARCHAR2(32 CHAR) NOT NULL, 
	id BIGINT NOT NULL IDENTITY(1, 1), 
	creator VARCHAR2(64 CHAR) NOT NULL, 
	create_time DATETIME NOT NULL, 
	updater VARCHAR2(64 CHAR) NOT NULL, 
	update_time DATETIME NOT NULL, 
	deleted SMALLINT NOT NULL, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_infra_api_error_log_tenant ON infra_api_error_log (tenant_id);
COMMENT ON TABLE infra_api_error_log IS 'API 错误日志表';
COMMENT ON COLUMN infra_api_error_log.trace_id IS '链路追踪编号';
COMMENT ON COLUMN infra_api_error_log.user_id IS '用户编号';
COMMENT ON COLUMN infra_api_error_log.user_type IS '用户类型（枚举）【UserTypeEnum】';
COMMENT ON COLUMN infra_api_error_log.application_name IS '应用名';
COMMENT ON COLUMN infra_api_error_log.request_method IS '请求方法名';
COMMENT ON COLUMN infra_api_error_log.request_url IS '访问地址';
COMMENT ON COLUMN infra_api_error_log.request_params IS '请求参数 (JSON格式)';
COMMENT ON COLUMN infra_api_error_log.user_ip IS '用户 IP';
COMMENT ON COLUMN infra_api_error_log.user_agent IS '浏览器 UA';
COMMENT ON COLUMN infra_api_error_log.exception_time IS '异常发生时间';
COMMENT ON COLUMN infra_api_error_log.exception_name IS '异常名';
COMMENT ON COLUMN infra_api_error_log.exception_message IS '异常导致的消息';
COMMENT ON COLUMN infra_api_error_log.exception_root_cause_message IS '异常导致的根消息';
COMMENT ON COLUMN infra_api_error_log.exception_stack_trace IS '异常的栈轨迹';
COMMENT ON COLUMN infra_api_error_log.exception_class_name IS '异常发生的类全名';
COMMENT ON COLUMN infra_api_error_log.exception_file_name IS '异常发生的类文件';
COMMENT ON COLUMN infra_api_error_log.exception_method_name IS '异常发生的方法名';
COMMENT ON COLUMN infra_api_error_log.exception_line_number IS '异常发生的方法所在行';
COMMENT ON COLUMN infra_api_error_log.process_status IS '处理状态';
COMMENT ON COLUMN infra_api_error_log.process_time IS '处理时间';
COMMENT ON COLUMN infra_api_error_log.process_user_id IS '处理用户编号';
COMMENT ON COLUMN infra_api_error_log.tenant_id IS '租户 ID（租户主键的字符串形式）';
COMMENT ON COLUMN infra_api_error_log.id IS '主键 ID';
COMMENT ON COLUMN infra_api_error_log.creator IS '创建者账号 ID';
COMMENT ON COLUMN infra_api_error_log.create_time IS '创建时间（UTC）';
COMMENT ON COLUMN infra_api_error_log.updater IS '更新者账号 ID';
COMMENT ON COLUMN infra_api_error_log.update_time IS '更新时间（UTC）';
COMMENT ON COLUMN infra_api_error_log.deleted IS '是否已删除';


-- infra_codegen_table：代码生成-表定义
CREATE TABLE infra_codegen_table (
	data_source_config_id BIGINT NOT NULL, 
	table_name VARCHAR2(200 CHAR) NOT NULL, 
	table_comment VARCHAR2(500 CHAR) NOT NULL, 
	class_name VARCHAR2(200 CHAR) NOT NULL, 
	author VARCHAR2(100 CHAR), 
	remark VARCHAR2(500 CHAR), 
	template_type SMALLINT NOT NULL, 
	front_type SMALLINT NOT NULL, 
	scene SMALLINT NOT NULL, 
	parent_menu_id BIGINT, 
	module_name VARCHAR2(100 CHAR) NOT NULL, 
	business_name VARCHAR2(100 CHAR) NOT NULL, 
	class_comment VARCHAR2(200 CHAR) NOT NULL, 
	enable_export SMALLINT NOT NULL, 
	tree_parent_column_id BIGINT, 
	tree_name_column_id BIGINT, 
	master_table_id BIGINT, 
	sub_join_column_id BIGINT, 
	sub_join_many SMALLINT, 
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN (deleted = 0) THEN 1 ELSE NULL END), 
	id BIGINT NOT NULL IDENTITY(1, 1), 
	creator VARCHAR2(64 CHAR) NOT NULL, 
	create_time DATETIME NOT NULL, 
	updater VARCHAR2(64 CHAR) NOT NULL, 
	update_time DATETIME NOT NULL, 
	deleted SMALLINT NOT NULL, 
	PRIMARY KEY (id)
);
CREATE UNIQUE INDEX uq_infra_codegen_table_active_0 ON infra_codegen_table (data_source_config_id, table_name, active_key, CASE WHEN active_key IS NOT NULL THEN NULL ELSE id END);
COMMENT ON TABLE infra_codegen_table IS '代码生成-表定义';
COMMENT ON COLUMN infra_codegen_table.data_source_config_id IS '数据源配置编号';
COMMENT ON COLUMN infra_codegen_table.table_name IS '表名称';
COMMENT ON COLUMN infra_codegen_table.table_comment IS '表描述';
COMMENT ON COLUMN infra_codegen_table.class_name IS '实体类名称';
COMMENT ON COLUMN infra_codegen_table.author IS '作者';
COMMENT ON COLUMN infra_codegen_table.remark IS '备注';
COMMENT ON COLUMN infra_codegen_table.template_type IS '模板类型: 1=CRUD, 2=Tree, 15=主子表';
COMMENT ON COLUMN infra_codegen_table.front_type IS '前端类型';
COMMENT ON COLUMN infra_codegen_table.scene IS '生成场景';
COMMENT ON COLUMN infra_codegen_table.parent_menu_id IS '父菜单编号';
COMMENT ON COLUMN infra_codegen_table.module_name IS '模块名，如 system、infra';
COMMENT ON COLUMN infra_codegen_table.business_name IS '业务名，如 user、dict';
COMMENT ON COLUMN infra_codegen_table.class_comment IS '类描述，如 用户';
COMMENT ON COLUMN infra_codegen_table.enable_export IS '是否启用导出';
COMMENT ON COLUMN infra_codegen_table.tree_parent_column_id IS '树表-父字段编号';
COMMENT ON COLUMN infra_codegen_table.tree_name_column_id IS '树表-名称字段编号';
COMMENT ON COLUMN infra_codegen_table.master_table_id IS '主子表-主表编号';
COMMENT ON COLUMN infra_codegen_table.sub_join_column_id IS '主子表-子表关联字段编号';
COMMENT ON COLUMN infra_codegen_table.sub_join_many IS '主子表-关联关系: true=一对多, false=一对一';
COMMENT ON COLUMN infra_codegen_table.active_key IS '仅有效记录参与业务唯一约束';
COMMENT ON COLUMN infra_codegen_table.id IS '主键 ID';
COMMENT ON COLUMN infra_codegen_table.creator IS '创建者账号 ID';
COMMENT ON COLUMN infra_codegen_table.create_time IS '创建时间（UTC）';
COMMENT ON COLUMN infra_codegen_table.updater IS '更新者账号 ID';
COMMENT ON COLUMN infra_codegen_table.update_time IS '更新时间（UTC）';
COMMENT ON COLUMN infra_codegen_table.deleted IS '是否已删除';


-- infra_config_type：配置类型表
CREATE TABLE infra_config_type (
	module VARCHAR2(50 CHAR) NOT NULL, 
	name VARCHAR2(100 CHAR) NOT NULL, 
	code VARCHAR2(100 CHAR) NOT NULL, 
	status SMALLINT NOT NULL, 
	remark VARCHAR2(500 CHAR), 
	deleted_time DATETIME, 
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN (deleted = 0) THEN 1 ELSE NULL END), 
	tenant_id VARCHAR2(32 CHAR) NOT NULL, 
	id BIGINT NOT NULL IDENTITY(1, 1), 
	creator VARCHAR2(64 CHAR) NOT NULL, 
	create_time DATETIME NOT NULL, 
	updater VARCHAR2(64 CHAR) NOT NULL, 
	update_time DATETIME NOT NULL, 
	deleted SMALLINT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_infra_config_type_tenant_id UNIQUE (tenant_id, id)
);
CREATE UNIQUE INDEX uq_infra_config_type_active_0 ON infra_config_type (tenant_id, code, active_key, CASE WHEN active_key IS NOT NULL THEN NULL ELSE id END);
CREATE INDEX ix_infra_config_type_tenant ON infra_config_type (tenant_id);
COMMENT ON TABLE infra_config_type IS '配置类型表';
COMMENT ON COLUMN infra_config_type.module IS '所属模块标识';
COMMENT ON COLUMN infra_config_type.name IS '配置类型名称';
COMMENT ON COLUMN infra_config_type.code IS '配置类型编码';
COMMENT ON COLUMN infra_config_type.status IS '状态（1-启用，0-禁用）';
COMMENT ON COLUMN infra_config_type.remark IS '备注';
COMMENT ON COLUMN infra_config_type.deleted_time IS '删除时间';
COMMENT ON COLUMN infra_config_type.active_key IS '仅有效记录参与业务唯一约束';
COMMENT ON COLUMN infra_config_type.tenant_id IS '租户 ID（租户主键的字符串形式）';
COMMENT ON COLUMN infra_config_type.id IS '主键 ID';
COMMENT ON COLUMN infra_config_type.creator IS '创建者账号 ID';
COMMENT ON COLUMN infra_config_type.create_time IS '创建时间（UTC）';
COMMENT ON COLUMN infra_config_type.updater IS '更新者账号 ID';
COMMENT ON COLUMN infra_config_type.update_time IS '更新时间（UTC）';
COMMENT ON COLUMN infra_config_type.deleted IS '是否已删除';


-- infra_data_source_config：数据源配置表
CREATE TABLE infra_data_source_config (
	name VARCHAR2(100 CHAR) NOT NULL, 
	url VARCHAR2(500 CHAR) NOT NULL, 
	status SMALLINT NOT NULL, 
	db_type VARCHAR2(50 CHAR) NOT NULL, 
	source_type SMALLINT NOT NULL, 
	is_default SMALLINT NOT NULL, 
	pool_size SMALLINT NOT NULL, 
	max_overflow SMALLINT NOT NULL, 
	pool_recycle SMALLINT NOT NULL, 
	pool_timeout SMALLINT NOT NULL, 
	echo SMALLINT NOT NULL, 
	remark VARCHAR2(500 CHAR), 
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN (deleted = 0) THEN 1 ELSE NULL END), 
	default_active SMALLINT GENERATED ALWAYS AS (CASE WHEN (deleted = 0 AND is_default = 1) THEN 1 ELSE NULL END), 
	id BIGINT NOT NULL IDENTITY(1, 1), 
	creator VARCHAR2(64 CHAR) NOT NULL, 
	create_time DATETIME NOT NULL, 
	updater VARCHAR2(64 CHAR) NOT NULL, 
	update_time DATETIME NOT NULL, 
	deleted SMALLINT NOT NULL, 
	PRIMARY KEY (id)
);
CREATE UNIQUE INDEX uq_infra_data_source_config_active_0 ON infra_data_source_config (name, active_key, CASE WHEN active_key IS NOT NULL THEN NULL ELSE id END);
CREATE UNIQUE INDEX uq_infra_data_source_config_default_active ON infra_data_source_config (source_type, default_active, CASE WHEN default_active IS NOT NULL THEN NULL ELSE id END);
COMMENT ON TABLE infra_data_source_config IS '数据源配置表';
COMMENT ON COLUMN infra_data_source_config.name IS '数据源名称';
COMMENT ON COLUMN infra_data_source_config.url IS '数据源连接URL';
COMMENT ON COLUMN infra_data_source_config.status IS '状态：1-启用，0-禁用';
COMMENT ON COLUMN infra_data_source_config.db_type IS '数据库类型';
COMMENT ON COLUMN infra_data_source_config.source_type IS '数据源类型：1-主库，2-从库';
COMMENT ON COLUMN infra_data_source_config.is_default IS '是否默认数据源';
COMMENT ON COLUMN infra_data_source_config.pool_size IS '连接池大小';
COMMENT ON COLUMN infra_data_source_config.max_overflow IS '最大溢出连接数';
COMMENT ON COLUMN infra_data_source_config.pool_recycle IS '连接最大复用时间（秒）';
COMMENT ON COLUMN infra_data_source_config.pool_timeout IS '获取连接最大等待时间（秒）';
COMMENT ON COLUMN infra_data_source_config.echo IS '是否开启SQL日志';
COMMENT ON COLUMN infra_data_source_config.remark IS '备注';
COMMENT ON COLUMN infra_data_source_config.active_key IS '仅有效记录参与业务唯一约束';
COMMENT ON COLUMN infra_data_source_config.default_active IS '有效默认配置唯一标记';
COMMENT ON COLUMN infra_data_source_config.id IS '主键 ID';
COMMENT ON COLUMN infra_data_source_config.creator IS '创建者账号 ID';
COMMENT ON COLUMN infra_data_source_config.create_time IS '创建时间（UTC）';
COMMENT ON COLUMN infra_data_source_config.updater IS '更新者账号 ID';
COMMENT ON COLUMN infra_data_source_config.update_time IS '更新时间（UTC）';
COMMENT ON COLUMN infra_data_source_config.deleted IS '是否已删除';


-- infra_file_config：文件配置表
CREATE TABLE infra_file_config (
	name VARCHAR2(100 CHAR) NOT NULL, 
	storage INTEGER NOT NULL, 
	remark TEXT, 
	status SMALLINT NOT NULL, 
	master SMALLINT NOT NULL, 
	config JSON NOT NULL, 
	master_active SMALLINT GENERATED ALWAYS AS (CASE WHEN (deleted = 0 AND master = 1) THEN 1 ELSE NULL END), 
	tenant_id VARCHAR2(32 CHAR) NOT NULL, 
	id BIGINT NOT NULL IDENTITY(1, 1), 
	creator VARCHAR2(64 CHAR) NOT NULL, 
	create_time DATETIME NOT NULL, 
	updater VARCHAR2(64 CHAR) NOT NULL, 
	update_time DATETIME NOT NULL, 
	deleted SMALLINT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_infra_file_config_tenant_id UNIQUE (tenant_id, id)
);
CREATE UNIQUE INDEX uq_infra_file_config_master_active ON infra_file_config (tenant_id, master_active, CASE WHEN master_active IS NOT NULL THEN NULL ELSE id END);
CREATE INDEX ix_infra_file_config_tenant ON infra_file_config (tenant_id);
COMMENT ON TABLE infra_file_config IS '文件配置表';
COMMENT ON COLUMN infra_file_config.name IS '配置名';
COMMENT ON COLUMN infra_file_config.storage IS '存储器（枚举类型）';
COMMENT ON COLUMN infra_file_config.remark IS '备注';
COMMENT ON COLUMN infra_file_config.status IS '状态（1-启用，0-禁用）';
COMMENT ON COLUMN infra_file_config.master IS '是否为主配置';
COMMENT ON COLUMN infra_file_config.config IS '文件客户端配置';
COMMENT ON COLUMN infra_file_config.master_active IS '有效默认配置唯一标记';
COMMENT ON COLUMN infra_file_config.tenant_id IS '租户 ID（租户主键的字符串形式）';
COMMENT ON COLUMN infra_file_config.id IS '主键 ID';
COMMENT ON COLUMN infra_file_config.creator IS '创建者账号 ID';
COMMENT ON COLUMN infra_file_config.create_time IS '创建时间（UTC）';
COMMENT ON COLUMN infra_file_config.updater IS '更新者账号 ID';
COMMENT ON COLUMN infra_file_config.update_time IS '更新时间（UTC）';
COMMENT ON COLUMN infra_file_config.deleted IS '是否已删除';


-- infra_job：定时任务 DO
CREATE TABLE infra_job (
	name VARCHAR2(255 CHAR) NOT NULL, 
	status INTEGER NOT NULL, 
	handler_name VARCHAR2(255 CHAR) NOT NULL, 
	handler_param VARCHAR2(512 CHAR), 
	cron_expression VARCHAR2(255 CHAR) NOT NULL, 
	retry_count INTEGER NOT NULL, 
	retry_interval INTEGER NOT NULL, 
	monitor_timeout INTEGER, 
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN (deleted = 0) THEN 1 ELSE NULL END), 
	revision VARCHAR2(64 CHAR) NOT NULL, 
	effective_at DATETIME NOT NULL, 
	parameters JSON NOT NULL, 
	tenant_id VARCHAR2(256 CHAR), 
	fan_out SMALLINT NOT NULL, 
	max_instances INTEGER NOT NULL, 
	timeout_seconds FLOAT NOT NULL, 
	retry_backoff FLOAT NOT NULL, 
	stop_after_failure SMALLINT NOT NULL, 
	id BIGINT NOT NULL IDENTITY(1, 1), 
	creator VARCHAR2(64 CHAR) NOT NULL, 
	create_time DATETIME NOT NULL, 
	updater VARCHAR2(64 CHAR) NOT NULL, 
	update_time DATETIME NOT NULL, 
	deleted SMALLINT NOT NULL, 
	PRIMARY KEY (id)
);
CREATE UNIQUE INDEX uq_infra_job_active_0 ON infra_job (handler_name, active_key, CASE WHEN active_key IS NOT NULL THEN NULL ELSE id END);
COMMENT ON TABLE infra_job IS '定时任务 DO';
COMMENT ON COLUMN infra_job.name IS '任务名称';
COMMENT ON COLUMN infra_job.status IS '任务状态，枚举 【JobStatusEnum】';
COMMENT ON COLUMN infra_job.handler_name IS '处理器的名字';
COMMENT ON COLUMN infra_job.handler_param IS '处理器的参数';
COMMENT ON COLUMN infra_job.cron_expression IS 'CRON 表达式';
COMMENT ON COLUMN infra_job.retry_count IS '重试次数，如果不重试，则设置为 0';
COMMENT ON COLUMN infra_job.retry_interval IS '重试间隔，单位：毫秒，如果没有间隔，则设置为 0';
COMMENT ON COLUMN infra_job.monitor_timeout IS '监控超时时间，单位：毫秒，为空时，表示不监控';
COMMENT ON COLUMN infra_job.active_key IS '仅有效记录参与业务唯一约束';
COMMENT ON COLUMN infra_job.revision IS '计划版本';
COMMENT ON COLUMN infra_job.effective_at IS '版本生效时间 UTC';
COMMENT ON COLUMN infra_job.parameters IS '经过 handler 参数模型验证的值';
COMMENT ON COLUMN infra_job.tenant_id IS '任务目标租户；控制面记录不参与行租户过滤';
COMMENT ON COLUMN infra_job.fan_out IS '是否向已授权租户扇出';
COMMENT ON COLUMN infra_job.max_instances IS '最大并发数';
COMMENT ON COLUMN infra_job.timeout_seconds IS '单次执行上限';
COMMENT ON COLUMN infra_job.retry_backoff IS '重试退避倍率';
COMMENT ON COLUMN infra_job.stop_after_failure IS '失败后停止匹配版本';
COMMENT ON COLUMN infra_job.id IS '主键 ID';
COMMENT ON COLUMN infra_job.creator IS '创建者账号 ID';
COMMENT ON COLUMN infra_job.create_time IS '创建时间（UTC）';
COMMENT ON COLUMN infra_job.updater IS '更新者账号 ID';
COMMENT ON COLUMN infra_job.update_time IS '更新时间（UTC）';
COMMENT ON COLUMN infra_job.deleted IS '是否已删除';


-- infra_job_log：定时任务的执行日志
CREATE TABLE infra_job_log (
	job_id BIGINT NOT NULL, 
	handler_name VARCHAR2(255 CHAR) NOT NULL, 
	handler_param VARCHAR2(512 CHAR), 
	execute_index INTEGER NOT NULL, 
	begin_time DATETIME, 
	end_time DATETIME, 
	duration INTEGER, 
	status INTEGER NOT NULL, 
	result VARCHAR2(4096 CHAR), 
	request_id VARCHAR2(128 CHAR) NOT NULL, 
	state VARCHAR2(32 CHAR) NOT NULL, 
	id BIGINT NOT NULL IDENTITY(1, 1), 
	creator VARCHAR2(64 CHAR) NOT NULL, 
	create_time DATETIME NOT NULL, 
	updater VARCHAR2(64 CHAR) NOT NULL, 
	update_time DATETIME NOT NULL, 
	deleted SMALLINT NOT NULL, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_infra_job_log_request_id ON infra_job_log (request_id);
COMMENT ON TABLE infra_job_log IS '定时任务的执行日志';
COMMENT ON COLUMN infra_job_log.job_id IS '任务编号，关联 JobDO.id';
COMMENT ON COLUMN infra_job_log.handler_name IS '处理器的名字，冗余字段 JobDO.handler_name';
COMMENT ON COLUMN infra_job_log.handler_param IS '处理器的参数，冗余字段 JobDO.handler_param';
COMMENT ON COLUMN infra_job_log.execute_index IS '第几次执行，用于区分是不是重试执行。如果是重试执行，则 index 大于 1';
COMMENT ON COLUMN infra_job_log.begin_time IS '开始执行时间';
COMMENT ON COLUMN infra_job_log.end_time IS '结束执行时间';
COMMENT ON COLUMN infra_job_log.duration IS '执行时长，单位：毫秒';
COMMENT ON COLUMN infra_job_log.status IS '状态，枚举 【JobLogStatusEnum】';
COMMENT ON COLUMN infra_job_log.result IS '结果数据，成功时是执行结果，失败时是异常堆栈';
COMMENT ON COLUMN infra_job_log.request_id IS '持久执行请求编号';
COMMENT ON COLUMN infra_job_log.state IS 'Native 执行终态';
COMMENT ON COLUMN infra_job_log.id IS '主键 ID';
COMMENT ON COLUMN infra_job_log.creator IS '创建者账号 ID';
COMMENT ON COLUMN infra_job_log.create_time IS '创建时间（UTC）';
COMMENT ON COLUMN infra_job_log.updater IS '更新者账号 ID';
COMMENT ON COLUMN infra_job_log.update_time IS '更新时间（UTC）';
COMMENT ON COLUMN infra_job_log.deleted IS '是否已删除';


-- infra_job_request：调度器持久协调记录
CREATE TABLE infra_job_request (
	request_id VARCHAR2(128 CHAR) NOT NULL, 
	job_id BIGINT NOT NULL, 
	request JSON NOT NULL, 
	state VARCHAR2(32 CHAR) NOT NULL, 
	owner VARCHAR2(128 CHAR), 
	ready_at DATETIME NOT NULL, 
	id BIGINT NOT NULL IDENTITY(1, 1), 
	creator VARCHAR2(64 CHAR) NOT NULL, 
	create_time DATETIME NOT NULL, 
	updater VARCHAR2(64 CHAR) NOT NULL, 
	update_time DATETIME NOT NULL, 
	deleted SMALLINT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT infra_job_request_request_id_key UNIQUE (request_id)
);
CREATE INDEX ix_infra_job_request_job_id ON infra_job_request (job_id);
CREATE INDEX ix_infra_job_request_ready_at ON infra_job_request (ready_at);
CREATE INDEX ix_infra_job_request_state ON infra_job_request (state);
COMMENT ON TABLE infra_job_request IS '调度器持久协调记录';
COMMENT ON COLUMN infra_job_request.request_id IS '跨进程幂等请求编号';
COMMENT ON COLUMN infra_job_request.job_id IS '任务编号';
COMMENT ON COLUMN infra_job_request.request IS 'Native JobRequest 快照';
COMMENT ON COLUMN infra_job_request.state IS 'pending/claimed/执行终态';
COMMENT ON COLUMN infra_job_request.owner IS '独占调度 owner';
COMMENT ON COLUMN infra_job_request.ready_at IS '允许领取时间 UTC';
COMMENT ON COLUMN infra_job_request.id IS '主键 ID';
COMMENT ON COLUMN infra_job_request.creator IS '创建者账号 ID';
COMMENT ON COLUMN infra_job_request.create_time IS '创建时间（UTC）';
COMMENT ON COLUMN infra_job_request.updater IS '更新者账号 ID';
COMMENT ON COLUMN infra_job_request.update_time IS '更新时间（UTC）';
COMMENT ON COLUMN infra_job_request.deleted IS '是否已删除';


-- infra_job_schedule：调度器持久协调记录
CREATE TABLE infra_job_schedule (
	job_id BIGINT NOT NULL, 
	checkpoint DATETIME NOT NULL, 
	id BIGINT NOT NULL IDENTITY(1, 1), 
	creator VARCHAR2(64 CHAR) NOT NULL, 
	create_time DATETIME NOT NULL, 
	updater VARCHAR2(64 CHAR) NOT NULL, 
	update_time DATETIME NOT NULL, 
	deleted SMALLINT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT infra_job_schedule_job_id_key UNIQUE (job_id)
);
COMMENT ON TABLE infra_job_schedule IS '调度器持久协调记录';
COMMENT ON COLUMN infra_job_schedule.job_id IS '任务编号';
COMMENT ON COLUMN infra_job_schedule.checkpoint IS '永久定时投递游标；不随历史请求清理';
COMMENT ON COLUMN infra_job_schedule.id IS '主键 ID';
COMMENT ON COLUMN infra_job_schedule.creator IS '创建者账号 ID';
COMMENT ON COLUMN infra_job_schedule.create_time IS '创建时间（UTC）';
COMMENT ON COLUMN infra_job_schedule.updater IS '更新者账号 ID';
COMMENT ON COLUMN infra_job_schedule.update_time IS '更新时间（UTC）';
COMMENT ON COLUMN infra_job_schedule.deleted IS '是否已删除';


-- infra_job_signal：调度器持久协调记录
CREATE TABLE infra_job_signal (
	revision BIGINT NOT NULL, 
	id BIGINT NOT NULL IDENTITY(1, 1), 
	creator VARCHAR2(64 CHAR) NOT NULL, 
	create_time DATETIME NOT NULL, 
	updater VARCHAR2(64 CHAR) NOT NULL, 
	update_time DATETIME NOT NULL, 
	deleted SMALLINT NOT NULL, 
	PRIMARY KEY (id)
);
COMMENT ON TABLE infra_job_signal IS '调度器持久协调记录';
COMMENT ON COLUMN infra_job_signal.revision IS '任务定义提交后的合并通知版本';
COMMENT ON COLUMN infra_job_signal.id IS '主键 ID';
COMMENT ON COLUMN infra_job_signal.creator IS '创建者账号 ID';
COMMENT ON COLUMN infra_job_signal.create_time IS '创建时间（UTC）';
COMMENT ON COLUMN infra_job_signal.updater IS '更新者账号 ID';
COMMENT ON COLUMN infra_job_signal.update_time IS '更新时间（UTC）';
COMMENT ON COLUMN infra_job_signal.deleted IS '是否已删除';


-- infra_mq：MQ 消息的定义
CREATE TABLE infra_mq (
	topic VARCHAR2(255 CHAR) NOT NULL, 
	consumer VARCHAR2(255 CHAR) NOT NULL, 
	retry_count INTEGER NOT NULL, 
	description VARCHAR2(512 CHAR), 
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN (deleted = 0) THEN 1 ELSE NULL END), 
	enabled SMALLINT NOT NULL, 
	concurrency INTEGER, 
	prefetch INTEGER, 
	id BIGINT NOT NULL IDENTITY(1, 1), 
	creator VARCHAR2(64 CHAR) NOT NULL, 
	create_time DATETIME NOT NULL, 
	updater VARCHAR2(64 CHAR) NOT NULL, 
	update_time DATETIME NOT NULL, 
	deleted SMALLINT NOT NULL, 
	PRIMARY KEY (id)
);
CREATE UNIQUE INDEX uq_infra_mq_active_0 ON infra_mq (consumer, active_key, CASE WHEN active_key IS NOT NULL THEN NULL ELSE id END);
COMMENT ON TABLE infra_mq IS 'MQ 消息的定义';
COMMENT ON COLUMN infra_mq.topic IS '消息主题 Topic';
COMMENT ON COLUMN infra_mq.consumer IS '消费者名称，即处理函数名';
COMMENT ON COLUMN infra_mq.retry_count IS '重试次数';
COMMENT ON COLUMN infra_mq.description IS '描述';
COMMENT ON COLUMN infra_mq.active_key IS '仅有效记录参与业务唯一约束';
COMMENT ON COLUMN infra_mq.enabled IS '部署覆盖开关';
COMMENT ON COLUMN infra_mq.concurrency IS '部署覆盖并发数';
COMMENT ON COLUMN infra_mq.prefetch IS '部署覆盖预取数';
COMMENT ON COLUMN infra_mq.id IS '主键 ID';
COMMENT ON COLUMN infra_mq.creator IS '创建者账号 ID';
COMMENT ON COLUMN infra_mq.create_time IS '创建时间（UTC）';
COMMENT ON COLUMN infra_mq.updater IS '更新者账号 ID';
COMMENT ON COLUMN infra_mq.update_time IS '更新时间（UTC）';
COMMENT ON COLUMN infra_mq.deleted IS '是否已删除';


-- infra_mq_log：MQ 消息的消费日志
CREATE TABLE infra_mq_log (
	message_id VARCHAR2(64 CHAR) NOT NULL, 
	topic VARCHAR2(255 CHAR) NOT NULL, 
	consumer VARCHAR2(255 CHAR) NOT NULL, 
	execute_index INTEGER NOT NULL, 
	begin_time DATETIME, 
	end_time DATETIME, 
	duration INTEGER, 
	status INTEGER NOT NULL, 
	result TEXT, 
	payload JSON, 
	state VARCHAR2(32 CHAR) NOT NULL, 
	id BIGINT NOT NULL IDENTITY(1, 1), 
	creator VARCHAR2(64 CHAR) NOT NULL, 
	create_time DATETIME NOT NULL, 
	updater VARCHAR2(64 CHAR) NOT NULL, 
	update_time DATETIME NOT NULL, 
	deleted SMALLINT NOT NULL, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_infra_mq_log_message_id ON infra_mq_log (message_id);
CREATE INDEX ix_infra_mq_log_topic ON infra_mq_log (topic);
COMMENT ON TABLE infra_mq_log IS 'MQ 消息的消费日志';
COMMENT ON COLUMN infra_mq_log.message_id IS '消息ID';
COMMENT ON COLUMN infra_mq_log.topic IS '消息主题';
COMMENT ON COLUMN infra_mq_log.consumer IS '消费者名称，冗余字段';
COMMENT ON COLUMN infra_mq_log.execute_index IS '第几次消费，用于区分是不是重试消费。如果是重试，则 index 大于 1';
COMMENT ON COLUMN infra_mq_log.begin_time IS '开始消费时间';
COMMENT ON COLUMN infra_mq_log.end_time IS '结束消费时间';
COMMENT ON COLUMN infra_mq_log.duration IS '消费时长，单位：毫秒';
COMMENT ON COLUMN infra_mq_log.status IS '状态，枚举 MqLogStatusEnum';
COMMENT ON COLUMN infra_mq_log.result IS '结果数据，成功时是执行结果，失败时是异常堆栈';
COMMENT ON COLUMN infra_mq_log.payload IS '仅留空字段承接历史表结构；不记录正文或身份凭证';
COMMENT ON COLUMN infra_mq_log.state IS 'Native 消费终态';
COMMENT ON COLUMN infra_mq_log.id IS '主键 ID';
COMMENT ON COLUMN infra_mq_log.creator IS '创建者账号 ID';
COMMENT ON COLUMN infra_mq_log.create_time IS '创建时间（UTC）';
COMMENT ON COLUMN infra_mq_log.updater IS '更新者账号 ID';
COMMENT ON COLUMN infra_mq_log.update_time IS '更新时间（UTC）';
COMMENT ON COLUMN infra_mq_log.deleted IS '是否已删除';


-- infra_mq_outbox：租户 MQ 可靠发布记录
CREATE TABLE infra_mq_outbox (
	record_id VARCHAR2(128 CHAR) NOT NULL, 
	message TEXT NOT NULL, 
	state VARCHAR2(16 CHAR) NOT NULL, 
	attempts INTEGER NOT NULL, 
	created_at_us BIGINT NOT NULL, 
	ready_at_us BIGINT NOT NULL, 
	claim_token VARCHAR2(32 CHAR), 
	claim_expires_at_us BIGINT, 
	finished_at_us BIGINT, 
	error_type TEXT, 
	settled_token VARCHAR2(32 CHAR), 
	receipt TEXT, 
	tenant_id VARCHAR2(32 CHAR) NOT NULL, 
	id BIGINT NOT NULL IDENTITY(1, 1), 
	creator VARCHAR2(64 CHAR) NOT NULL, 
	create_time DATETIME NOT NULL, 
	updater VARCHAR2(64 CHAR) NOT NULL, 
	update_time DATETIME NOT NULL, 
	deleted SMALLINT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uk_mq_outbox_tenant_record UNIQUE (tenant_id, record_id)
);
CREATE INDEX idx_mq_outbox_lease ON infra_mq_outbox (tenant_id, state, claim_expires_at_us);
CREATE INDEX idx_mq_outbox_ready ON infra_mq_outbox (tenant_id, state, ready_at_us);
COMMENT ON TABLE infra_mq_outbox IS '租户 MQ 可靠发布记录';
COMMENT ON COLUMN infra_mq_outbox.record_id IS '入箱幂等编号';
COMMENT ON COLUMN infra_mq_outbox.message IS 'PreparedMessage 原始 JSON 文本';
COMMENT ON COLUMN infra_mq_outbox.state IS '可靠发布状态';
COMMENT ON COLUMN infra_mq_outbox.attempts IS '已认领次数';
COMMENT ON COLUMN infra_mq_outbox.created_at_us IS '入箱时间 UTC 微秒';
COMMENT ON COLUMN infra_mq_outbox.ready_at_us IS '允许发布时间 UTC 微秒';
COMMENT ON COLUMN infra_mq_outbox.claim_token IS '当前认领令牌';
COMMENT ON COLUMN infra_mq_outbox.claim_expires_at_us IS '租约截止 UTC 微秒';
COMMENT ON COLUMN infra_mq_outbox.finished_at_us IS '结算时间 UTC 微秒';
COMMENT ON COLUMN infra_mq_outbox.error_type IS '失败异常类型';
COMMENT ON COLUMN infra_mq_outbox.settled_token IS '已结算认领令牌';
COMMENT ON COLUMN infra_mq_outbox.receipt IS 'Broker 确认回执 JSON';
COMMENT ON COLUMN infra_mq_outbox.tenant_id IS '租户 ID（租户主键的字符串形式）';
COMMENT ON COLUMN infra_mq_outbox.id IS '主键 ID';
COMMENT ON COLUMN infra_mq_outbox.creator IS '创建者账号 ID';
COMMENT ON COLUMN infra_mq_outbox.create_time IS '创建时间（UTC）';
COMMENT ON COLUMN infra_mq_outbox.updater IS '更新者账号 ID';
COMMENT ON COLUMN infra_mq_outbox.update_time IS '更新时间（UTC）';
COMMENT ON COLUMN infra_mq_outbox.deleted IS '是否已删除';


-- infra_tenant_job_target：定时任务逐租户执行与认领记录
CREATE TABLE infra_tenant_job_target (
	request_id VARCHAR2(128 CHAR) NOT NULL, 
	tenant_id VARCHAR2(256 CHAR) NOT NULL, 
	state VARCHAR2(16 CHAR) NOT NULL, 
	token VARCHAR2(32 CHAR) NOT NULL, 
	expires_at_us BIGINT NOT NULL, 
	id BIGINT NOT NULL IDENTITY(1, 1), 
	creator VARCHAR2(64 CHAR) NOT NULL, 
	create_time DATETIME NOT NULL, 
	updater VARCHAR2(64 CHAR) NOT NULL, 
	update_time DATETIME NOT NULL, 
	deleted SMALLINT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_infra_tenant_job_target UNIQUE (request_id, tenant_id)
);
COMMENT ON TABLE infra_tenant_job_target IS '定时任务逐租户执行与认领记录';
COMMENT ON COLUMN infra_tenant_job_target.request_id IS '调度请求编号';
COMMENT ON COLUMN infra_tenant_job_target.tenant_id IS '执行目标租户；控制面记录不参与租户行过滤';
COMMENT ON COLUMN infra_tenant_job_target.state IS 'pending/claimed/completed/unknown';
COMMENT ON COLUMN infra_tenant_job_target.token IS '本次认领凭证';
COMMENT ON COLUMN infra_tenant_job_target.expires_at_us IS '认领到期 UTC Unix 微秒，跨数据库保持精度';
COMMENT ON COLUMN infra_tenant_job_target.id IS '主键 ID';
COMMENT ON COLUMN infra_tenant_job_target.creator IS '创建者账号 ID';
COMMENT ON COLUMN infra_tenant_job_target.create_time IS '创建时间（UTC）';
COMMENT ON COLUMN infra_tenant_job_target.updater IS '更新者账号 ID';
COMMENT ON COLUMN infra_tenant_job_target.update_time IS '更新时间（UTC）';
COMMENT ON COLUMN infra_tenant_job_target.deleted IS '是否已删除';


-- infra_codegen_column：代码生成-列定义
CREATE TABLE infra_codegen_column (
	table_id BIGINT NOT NULL, 
	column_name VARCHAR2(200 CHAR) NOT NULL, 
	column_comment VARCHAR2(500 CHAR) NOT NULL, 
	data_type VARCHAR2(100 CHAR) NOT NULL, 
	column_size BIGINT, 
	numeric_precision BIGINT, 
	numeric_scale BIGINT, 
	type_metadata_synced SMALLINT NOT NULL, 
	field_type VARCHAR2(50 CHAR) NOT NULL, 
	field_name VARCHAR2(200 CHAR) NOT NULL, 
	create_operation SMALLINT NOT NULL, 
	update_operation SMALLINT NOT NULL, 
	list_operation SMALLINT NOT NULL, 
	list_operation_result SMALLINT NOT NULL, 
	list_operation_condition VARCHAR2(20 CHAR) NOT NULL, 
	nullable SMALLINT NOT NULL, 
	html_type VARCHAR2(50 CHAR) NOT NULL, 
	dict_type VARCHAR2(200 CHAR), 
	example VARCHAR2(500 CHAR), 
	order_no SMALLINT NOT NULL, 
	primary_key SMALLINT NOT NULL, 
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN (deleted = 0) THEN 1 ELSE NULL END), 
	computed_expression TEXT, 
	computed_persisted SMALLINT, 
	id BIGINT NOT NULL IDENTITY(1, 1), 
	creator VARCHAR2(64 CHAR) NOT NULL, 
	create_time DATETIME NOT NULL, 
	updater VARCHAR2(64 CHAR) NOT NULL, 
	update_time DATETIME NOT NULL, 
	deleted SMALLINT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT fk_infra_codegen_column_table_id FOREIGN KEY(table_id) REFERENCES infra_codegen_table (id)
);
CREATE UNIQUE INDEX uq_infra_codegen_column_active_0 ON infra_codegen_column (table_id, column_name, active_key, CASE WHEN active_key IS NOT NULL THEN NULL ELSE id END);
COMMENT ON TABLE infra_codegen_column IS '代码生成-列定义';
COMMENT ON COLUMN infra_codegen_column.table_id IS '表编号';
COMMENT ON COLUMN infra_codegen_column.column_name IS '字段列名';
COMMENT ON COLUMN infra_codegen_column.column_comment IS '字段描述';
COMMENT ON COLUMN infra_codegen_column.data_type IS '字段物理类型';
COMMENT ON COLUMN infra_codegen_column.column_size IS '字段长度';
COMMENT ON COLUMN infra_codegen_column.numeric_precision IS '数值精度';
COMMENT ON COLUMN infra_codegen_column.numeric_scale IS '数值小数位数';
COMMENT ON COLUMN infra_codegen_column.type_metadata_synced IS '已同步完整物理类型';
COMMENT ON COLUMN infra_codegen_column.field_type IS 'Python字段类型';
COMMENT ON COLUMN infra_codegen_column.field_name IS 'Python属性名';
COMMENT ON COLUMN infra_codegen_column.create_operation IS '是否参与新增操作';
COMMENT ON COLUMN infra_codegen_column.update_operation IS '是否参与编辑操作';
COMMENT ON COLUMN infra_codegen_column.list_operation IS '是否作为查询条件';
COMMENT ON COLUMN infra_codegen_column.list_operation_result IS '是否在列表中展示';
COMMENT ON COLUMN infra_codegen_column.list_operation_condition IS '查询方式: =, !=, >, >=, <, <=, LIKE, BETWEEN';
COMMENT ON COLUMN infra_codegen_column.nullable IS '是否允许为空';
COMMENT ON COLUMN infra_codegen_column.html_type IS '显示类型: input, textarea, select, radio, checkbox, datetime, imageUpload, fileUpload, editor';
COMMENT ON COLUMN infra_codegen_column.dict_type IS '关联字典类型';
COMMENT ON COLUMN infra_codegen_column.example IS '示例值';
COMMENT ON COLUMN infra_codegen_column.order_no IS '排序';
COMMENT ON COLUMN infra_codegen_column.primary_key IS '是否主键';
COMMENT ON COLUMN infra_codegen_column.active_key IS '仅有效记录参与业务唯一约束';
COMMENT ON COLUMN infra_codegen_column.computed_expression IS '数据库生成列表达式';
COMMENT ON COLUMN infra_codegen_column.computed_persisted IS '生成列是否持久化';
COMMENT ON COLUMN infra_codegen_column.id IS '主键 ID';
COMMENT ON COLUMN infra_codegen_column.creator IS '创建者账号 ID';
COMMENT ON COLUMN infra_codegen_column.create_time IS '创建时间（UTC）';
COMMENT ON COLUMN infra_codegen_column.updater IS '更新者账号 ID';
COMMENT ON COLUMN infra_codegen_column.update_time IS '更新时间（UTC）';
COMMENT ON COLUMN infra_codegen_column.deleted IS '是否已删除';


-- infra_config_data：参数配置表
CREATE TABLE infra_config_data (
	type_id BIGINT NOT NULL, 
	name VARCHAR2(100 CHAR) NOT NULL, 
	key VARCHAR2(100 CHAR) NOT NULL, 
	"value" VARCHAR2(500 CHAR) NOT NULL, 
	description VARCHAR2(500 CHAR), 
	input_type VARCHAR2(50 CHAR), 
	input_props TEXT, 
	sort INTEGER NOT NULL, 
	visible INTEGER NOT NULL, 
	remark VARCHAR2(500 CHAR), 
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN (deleted = 0) THEN 1 ELSE NULL END), 
	tenant_id VARCHAR2(32 CHAR) NOT NULL, 
	id BIGINT NOT NULL IDENTITY(1, 1), 
	creator VARCHAR2(64 CHAR) NOT NULL, 
	create_time DATETIME NOT NULL, 
	updater VARCHAR2(64 CHAR) NOT NULL, 
	update_time DATETIME NOT NULL, 
	deleted SMALLINT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT fk_infra_config_data_type_id FOREIGN KEY(tenant_id, type_id) REFERENCES infra_config_type (tenant_id, id)
);
CREATE UNIQUE INDEX uq_infra_config_data_active_0 ON infra_config_data (tenant_id, key, active_key, CASE WHEN active_key IS NOT NULL THEN NULL ELSE id END);
CREATE INDEX ix_infra_config_data_tenant ON infra_config_data (tenant_id);
COMMENT ON TABLE infra_config_data IS '参数配置表';
COMMENT ON COLUMN infra_config_data.type_id IS '配置类型ID';
COMMENT ON COLUMN infra_config_data.name IS '参数名称';
COMMENT ON COLUMN infra_config_data.key IS '参数键名';
COMMENT ON COLUMN infra_config_data."value" IS '参数键值';
COMMENT ON COLUMN infra_config_data.description IS '配置描述';
COMMENT ON COLUMN infra_config_data.input_type IS 'UI控件类型';
COMMENT ON COLUMN infra_config_data.input_props IS 'UI控件属性JSON';
COMMENT ON COLUMN infra_config_data.sort IS '显示顺序';
COMMENT ON COLUMN infra_config_data.visible IS '是否可见';
COMMENT ON COLUMN infra_config_data.remark IS '备注';
COMMENT ON COLUMN infra_config_data.active_key IS '仅有效记录参与业务唯一约束';
COMMENT ON COLUMN infra_config_data.tenant_id IS '租户 ID（租户主键的字符串形式）';
COMMENT ON COLUMN infra_config_data.id IS '主键 ID';
COMMENT ON COLUMN infra_config_data.creator IS '创建者账号 ID';
COMMENT ON COLUMN infra_config_data.create_time IS '创建时间（UTC）';
COMMENT ON COLUMN infra_config_data.updater IS '更新者账号 ID';
COMMENT ON COLUMN infra_config_data.update_time IS '更新时间（UTC）';
COMMENT ON COLUMN infra_config_data.deleted IS '是否已删除';


-- infra_file：文件表
CREATE TABLE infra_file (
	config_id BIGINT NOT NULL, 
	name VARCHAR2(255 CHAR) NOT NULL, 
	original_name VARCHAR2(255 CHAR) NOT NULL, 
	path VARCHAR2(255 CHAR) NOT NULL, 
	storage_path VARCHAR2(1000 CHAR) NOT NULL, 
	url VARCHAR2(255 CHAR) NOT NULL, 
	visibility VARCHAR2(16 CHAR) NOT NULL, 
	type VARCHAR2(255 CHAR) NOT NULL, 
	"size" INTEGER NOT NULL, 
	hash VARCHAR2(64 CHAR), 
	file_metadata JSON, 
	tenant_id VARCHAR2(32 CHAR) NOT NULL, 
	id BIGINT NOT NULL IDENTITY(1, 1), 
	creator VARCHAR2(64 CHAR) NOT NULL, 
	create_time DATETIME NOT NULL, 
	updater VARCHAR2(64 CHAR) NOT NULL, 
	update_time DATETIME NOT NULL, 
	deleted SMALLINT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT fk_infra_file_config_id FOREIGN KEY(tenant_id, config_id) REFERENCES infra_file_config (tenant_id, id)
);
CREATE INDEX ix_infra_file_tenant ON infra_file (tenant_id);
COMMENT ON TABLE infra_file IS '文件表';
COMMENT ON COLUMN infra_file.config_id IS '配置编号';
COMMENT ON COLUMN infra_file.name IS '原文件名';
COMMENT ON COLUMN infra_file.original_name IS '原始文件名';
COMMENT ON COLUMN infra_file.path IS '路径，即文件名';
COMMENT ON COLUMN infra_file.storage_path IS '实际存储路径';
COMMENT ON COLUMN infra_file.url IS '访问地址';
COMMENT ON COLUMN infra_file.visibility IS '可见性';
COMMENT ON COLUMN infra_file.type IS '文件的 MIME 类型';
COMMENT ON COLUMN infra_file."size" IS '文件大小';
COMMENT ON COLUMN infra_file.hash IS '文件哈希值';
COMMENT ON COLUMN infra_file.file_metadata IS '文件元数据';
COMMENT ON COLUMN infra_file.tenant_id IS '租户 ID（租户主键的字符串形式）';
COMMENT ON COLUMN infra_file.id IS '主键 ID';
COMMENT ON COLUMN infra_file.creator IS '创建者账号 ID';
COMMENT ON COLUMN infra_file.create_time IS '创建时间（UTC）';
COMMENT ON COLUMN infra_file.updater IS '更新者账号 ID';
COMMENT ON COLUMN infra_file.update_time IS '更新时间（UTC）';
COMMENT ON COLUMN infra_file.deleted IS '是否已删除';


-- infra_file_content：文件内容表
CREATE TABLE infra_file_content (
	config_id BIGINT NOT NULL, 
	path VARCHAR2(255 CHAR) NOT NULL, 
	content BLOB NOT NULL, 
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN (deleted = 0) THEN 1 ELSE NULL END), 
	tenant_id VARCHAR2(32 CHAR) NOT NULL, 
	id BIGINT NOT NULL IDENTITY(1, 1), 
	creator VARCHAR2(64 CHAR) NOT NULL, 
	create_time DATETIME NOT NULL, 
	updater VARCHAR2(64 CHAR) NOT NULL, 
	update_time DATETIME NOT NULL, 
	deleted SMALLINT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT fk_infra_file_content_config_id FOREIGN KEY(tenant_id, config_id) REFERENCES infra_file_config (tenant_id, id)
);
CREATE UNIQUE INDEX uq_infra_file_content_active_0 ON infra_file_content (tenant_id, config_id, path, active_key, CASE WHEN active_key IS NOT NULL THEN NULL ELSE id END);
CREATE INDEX ix_infra_file_content_tenant ON infra_file_content (tenant_id);
COMMENT ON TABLE infra_file_content IS '文件内容表';
COMMENT ON COLUMN infra_file_content.config_id IS '配置编号';
COMMENT ON COLUMN infra_file_content.path IS '路径，即文件名';
COMMENT ON COLUMN infra_file_content.content IS '文件内容';
COMMENT ON COLUMN infra_file_content.active_key IS '仅有效记录参与业务唯一约束';
COMMENT ON COLUMN infra_file_content.tenant_id IS '租户 ID（租户主键的字符串形式）';
COMMENT ON COLUMN infra_file_content.id IS '主键 ID';
COMMENT ON COLUMN infra_file_content.creator IS '创建者账号 ID';
COMMENT ON COLUMN infra_file_content.create_time IS '创建时间（UTC）';
COMMENT ON COLUMN infra_file_content.updater IS '更新者账号 ID';
COMMENT ON COLUMN infra_file_content.update_time IS '更新时间（UTC）';
COMMENT ON COLUMN infra_file_content.deleted IS '是否已删除';
