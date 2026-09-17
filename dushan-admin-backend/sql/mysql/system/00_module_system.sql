-- module_system 建表脚本
-- 数据库方言：mysql
-- 本文件由模型导出生成，请勿手工修改；表结构变更请改模型后重新导出。


-- system_authorization_revision：系统授权版本
CREATE TABLE system_authorization_revision (
	revision BIGINT NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)COMMENT='系统授权版本' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;


-- system_dept：部门信息表
CREATE TABLE system_dept (
	name VARCHAR(30) NOT NULL COMMENT '部门名称',
	parent_id BIGINT NOT NULL COMMENT '父部门id',
	sort INTEGER NOT NULL COMMENT '显示顺序',
	leader_user_id BIGINT COMMENT '负责人',
	phone VARCHAR(11) COMMENT '联系电话',
	email VARCHAR(50) COMMENT '邮箱',
	status SMALLINT NOT NULL COMMENT '开启状态（1-启用，0-禁用）【StatusEnum】',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_system_dept_tenant_id UNIQUE (tenant_id, id)
)COMMENT='部门信息表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_dept_tenant ON system_dept (tenant_id);


-- system_dict_data：字典数据表
CREATE TABLE system_dict_data (
	sort INTEGER NOT NULL COMMENT '字典排序',
	label VARCHAR(100) NOT NULL COMMENT '字典标签',
	value VARCHAR(100) NOT NULL COMMENT '字典键值',
	dict_type VARCHAR(100) NOT NULL COMMENT '字典类型',
	status SMALLINT NOT NULL COMMENT '开启状态（1-启用，0-禁用）',
	color_type VARCHAR(100) COMMENT '颜色类型',
	tag_style JSON COMMENT '按钮样式',
	permission VARCHAR(100) COMMENT '权限标识（该选项所需的权限码，NULL表示无需权限）',
	remark VARCHAR(500) COMMENT '备注',
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)COMMENT='字典数据表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;


-- system_dict_type：字典类型表
CREATE TABLE system_dict_type (
	name VARCHAR(100) NOT NULL COMMENT '字典名称',
	type VARCHAR(100) NOT NULL COMMENT '字典类型',
	status SMALLINT NOT NULL COMMENT '开启状态（1-启用，0-禁用）',
	remark VARCHAR(500) COMMENT '备注',
	deleted_time DATETIME COMMENT '删除时间',
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)COMMENT='字典类型表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;


-- system_login_log：系统访问记录
CREATE TABLE system_login_log (
	log_type SMALLINT NOT NULL COMMENT '日志类型（枚举）【LoginLogTypeEnum】',
	trace_id VARCHAR(64) NOT NULL COMMENT '链路追踪编号',
	user_id BIGINT NOT NULL COMMENT '用户编号',
	user_type SMALLINT NOT NULL COMMENT '用户类型（枚举）【UserTypeEnum】',
	username VARCHAR(50) NOT NULL COMMENT '用户账号',
	result SMALLINT NOT NULL COMMENT '登录结果（枚举）【LoggerLoginResultEnum】',
	user_ip VARCHAR(50) NOT NULL COMMENT '用户IP',
	user_agent VARCHAR(512) NOT NULL COMMENT '浏览器UA',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)COMMENT='系统访问记录' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_login_log_tenant ON system_login_log (tenant_id);


-- system_mail_account：邮箱账号表
CREATE TABLE system_mail_account (
	mail VARCHAR(255) NOT NULL COMMENT '邮箱',
	username VARCHAR(255) NOT NULL COMMENT '用户名',
	password VARCHAR(255) NOT NULL COMMENT '密码',
	host VARCHAR(255) NOT NULL COMMENT 'SMTP 服务器域名',
	port INTEGER NOT NULL COMMENT 'SMTP 服务器端口',
	ssl_enable BOOL NOT NULL COMMENT '是否开启 SSL',
	starttls_enable BOOL NOT NULL COMMENT '是否开启 STARTTLS',
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)COMMENT='邮箱账号表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;


-- system_mail_log：邮件日志表
CREATE TABLE system_mail_log (
	user_id BIGINT COMMENT '用户编号',
	user_type SMALLINT NOT NULL COMMENT '用户类型（枚举）【UserTypeEnum】',
	to_mail TEXT NOT NULL COMMENT '接收邮箱地址(多个逗号分隔)',
	cc_mail TEXT COMMENT '抄送邮箱地址(多个逗号分隔)',
	bcc_mail TEXT COMMENT '密送邮箱地址(多个逗号分隔)',
	account_id BIGINT NOT NULL COMMENT '邮箱账号编号',
	from_mail VARCHAR(255) NOT NULL COMMENT '发送邮箱地址',
	template_id BIGINT NOT NULL COMMENT '模板编号',
	template_code VARCHAR(63) NOT NULL COMMENT '模板编码',
	template_nickname VARCHAR(255) COMMENT '模版发送人名称',
	template_title VARCHAR(255) NOT NULL COMMENT '邮件标题',
	template_content TEXT NOT NULL COMMENT '邮件内容',
	template_params JSON NOT NULL COMMENT '邮件参数',
	send_status SMALLINT NOT NULL COMMENT '发送状态【MailSendStatusEnum】',
	send_time DATETIME COMMENT '发送时间',
	send_message_id VARCHAR(255) COMMENT '发送返回的消息 ID',
	send_exception TEXT COMMENT '发送异常',
	send_claim_token VARCHAR(32) COMMENT '外发 claim 令牌',
	send_claim_until DATETIME COMMENT '外发前 claim 到期时间',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)COMMENT='邮件日志表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;


-- system_mail_template：邮件模版表
CREATE TABLE system_mail_template (
	name VARCHAR(63) NOT NULL COMMENT '模板名称',
	code VARCHAR(63) NOT NULL COMMENT '模板编码',
	account_id BIGINT NOT NULL COMMENT '发送的邮箱账号编号',
	nickname VARCHAR(255) COMMENT '发送人名称',
	title VARCHAR(255) NOT NULL COMMENT '模板标题',
	content TEXT NOT NULL COMMENT '模板内容',
	params JSON NOT NULL COMMENT '参数数组',
	status SMALLINT NOT NULL COMMENT '开启状态（1-启用，0-禁用）',
	remark VARCHAR(255) COMMENT '备注',
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)COMMENT='邮件模版表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;


-- system_menu：菜单权限表
CREATE TABLE system_menu (
	name VARCHAR(50) NOT NULL COMMENT '菜单名称',
	permission VARCHAR(100) NOT NULL COMMENT '权限标识',
	kind VARCHAR(16) NOT NULL COMMENT '菜单种类：group/page/action/link/iframe',
	data_permission BOOL NOT NULL COMMENT '是否为数据权限操作，承接源 DATA 类型',
	url VARCHAR(2048) COMMENT '外链或内嵌页面地址',
	sort INTEGER NOT NULL COMMENT '显示顺序',
	parent_id BIGINT NOT NULL COMMENT '父菜单ID',
	path VARCHAR(200) NOT NULL COMMENT '路由地址',
	icon VARCHAR(100) NOT NULL COMMENT '菜单图标',
	component VARCHAR(255) COMMENT '组件路径',
	component_name VARCHAR(255) COMMENT '组件名',
	status SMALLINT NOT NULL COMMENT '开启状态（1-启用，0-禁用）',
	visible BOOL NOT NULL COMMENT '是否可见',
	keep_alive BOOL NOT NULL COMMENT '是否缓存',
	always_show BOOL NOT NULL COMMENT '是否总是显示',
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)COMMENT='菜单权限表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;


-- system_announcement：公告表
CREATE TABLE system_announcement (
	title VARCHAR(100) NOT NULL COMMENT '公告标题',
	content TEXT NOT NULL COMMENT '公告内容',
	status SMALLINT NOT NULL COMMENT '公告状态（0-草稿，1-待发布，2-已发布，3-已过期）',
	is_top BOOL NOT NULL COMMENT '是否置顶',
	sort INTEGER NOT NULL COMMENT '排序序号（数值越小越靠前）',
	category SMALLINT NOT NULL COMMENT '公告类别，参见 AnnouncementCategoryEnum',
	publish_time DATETIME COMMENT '发布时间',
	expire_time DATETIME COMMENT '过期时间',
	publisher VARCHAR(64) NOT NULL COMMENT '发布人',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)COMMENT='公告表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_announcement_tenant ON system_announcement (tenant_id);


-- system_notification_message：站内信消息表
CREATE TABLE system_notification_message (
	user_id BIGINT NOT NULL COMMENT '用户id',
	user_type SMALLINT NOT NULL COMMENT '用户类型（枚举）【UserTypeEnum】',
	notice_id BIGINT NOT NULL COMMENT '关联的通知编号',
	notice_log_id BIGINT COMMENT '通知日志ID (system_notification_notice_log.id)',
	notice_title VARCHAR(100) NOT NULL COMMENT '通知标题',
	notice_content TEXT NOT NULL COMMENT '通知内容',
	notice_type INTEGER NOT NULL COMMENT '通知类型',
	publisher_info JSON COMMENT '发布者信息',
	sent_channels JSON NOT NULL COMMENT '实际发送的渠道,参见 NotificationChannelEnum',
	read_status BOOL NOT NULL COMMENT '是否已读',
	read_time DATETIME COMMENT '阅读时间',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)COMMENT='站内信消息表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_notification_message_tenant ON system_notification_message (tenant_id);


-- system_notification_notice：通知表
CREATE TABLE system_notification_notice (
	code VARCHAR(63) COMMENT '通知编码',
	builtin SMALLINT NOT NULL COMMENT '内置类型（1-内置 2-自定义）【BuiltinTypeEnum】',
	title VARCHAR(50) NOT NULL COMMENT '通知标题',
	content TEXT NOT NULL COMMENT '通知内容',
	type INTEGER NOT NULL COMMENT '通知类型【NoticeTypeEnum】',
	user_type SMALLINT NOT NULL COMMENT '用户类型【UserTypeEnum】',
	channels JSON NOT NULL COMMENT '通知渠道,参见 NotificationChannelEnum',
	sms_template_code VARCHAR(63) COMMENT '短信模板编码,选择SMS渠道时必填',
	mail_account_id BIGINT COMMENT '邮箱账号编号,选择MAIL渠道时必填',
	publisher VARCHAR(64) NOT NULL COMMENT '发布人',
	status SMALLINT NOT NULL COMMENT '开启状态（1-启用，0-禁用）',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)COMMENT='通知表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_notification_notice_tenant ON system_notification_notice (tenant_id);


-- system_notification_notice_log：通知日志表
CREATE TABLE system_notification_notice_log (
	notice_id BIGINT NOT NULL COMMENT '关联的通知编号',
	notice_title VARCHAR(100) NOT NULL COMMENT '通知标题(冗余快照)',
	notice_type INTEGER NOT NULL COMMENT '通知类型(冗余快照)',
	push_target_type SMALLINT NOT NULL COMMENT '推送目标类型(NoticePushTargetTypeEnum): 1=按用户, 2=按部门, 3=混合',
	target_user_ids JSON COMMENT '目标用户ID列表(原始选择)',
	target_dept_ids JSON COMMENT '目标部门ID列表(原始选择)',
	target_dept_names JSON COMMENT '目标部门名称列表(冗余快照)',
	push_channels JSON NOT NULL COMMENT '推送渠道',
	total_count INTEGER NOT NULL COMMENT '推送总人数',
	success_count INTEGER NOT NULL COMMENT '成功数',
	fail_count INTEGER NOT NULL COMMENT '失败数',
	push_status SMALLINT NOT NULL COMMENT '推送状态(NoticePushStatusEnum): 0=推送中, 1=全部成功, 2=部分失败, 3=全部失败',
	publisher_info JSON COMMENT '发布者信息',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)COMMENT='通知日志表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_notification_notice_log_tenant ON system_notification_notice_log (tenant_id);


-- system_oauth2_approve：OAuth2 批准表
CREATE TABLE system_oauth2_approve (
	user_id BIGINT NOT NULL COMMENT '用户编号',
	user_type SMALLINT NOT NULL COMMENT '用户类型（枚举）【UserTypeEnum】',
	client_id VARCHAR(255) NOT NULL COMMENT '客户端编号',
	scope VARCHAR(255) NOT NULL COMMENT '授权范围',
	approved BOOL NOT NULL COMMENT '是否接受',
	expires_time DATETIME NOT NULL COMMENT '过期时间',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)COMMENT='OAuth2 批准表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_oauth2_approve_tenant ON system_oauth2_approve (tenant_id);


-- system_oauth2_client：OAuth2 客户端表
CREATE TABLE system_oauth2_client (
	client_id VARCHAR(255) NOT NULL COMMENT '客户端编号',
	secret VARCHAR(255) NOT NULL COMMENT '客户端密钥',
	name VARCHAR(255) NOT NULL COMMENT '应用名',
	logo VARCHAR(255) NOT NULL COMMENT '应用图标',
	description VARCHAR(255) COMMENT '应用描述',
	status SMALLINT NOT NULL COMMENT '状态',
	user_type SMALLINT COMMENT '绑定的用户类型',
	access_token_validity_seconds INTEGER NOT NULL COMMENT '访问令牌的有效期',
	refresh_token_validity_seconds INTEGER NOT NULL COMMENT '刷新令牌的有效期',
	redirect_uris JSON NOT NULL COMMENT '可重定向的 URI 地址 (JSON 数组)',
	authorized_grant_types JSON NOT NULL COMMENT '授权类型 (JSON 数组)',
	scopes JSON COMMENT '授权范围 (JSON 数组)',
	auto_approve_scopes JSON COMMENT '自动通过的授权范围 (JSON 数组)',
	authorities JSON COMMENT '权限 (JSON 数组)',
	resource_ids JSON COMMENT '资源 (JSON 数组)',
	additional_information VARCHAR(255) COMMENT '附加信息',
	credential_revision INTEGER NOT NULL COMMENT '???????',
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (client_id)
)COMMENT='OAuth2 客户端表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;


-- system_oauth2_code：OAuth2 授权码表
CREATE TABLE system_oauth2_code (
	user_id BIGINT NOT NULL COMMENT '用户编号',
	user_type SMALLINT NOT NULL COMMENT '用户类型（枚举）【UserTypeEnum】',
	code_digest VARCHAR(64) NOT NULL COMMENT '授权码 SHA-256 摘要',
	client_id VARCHAR(255) NOT NULL COMMENT '客户端编号',
	scopes JSON COMMENT '授权范围 (JSON 数组)',
	expires_time DATETIME NOT NULL COMMENT '过期时间',
	redirect_uri VARCHAR(255) COMMENT '可重定向的 URI 地址',
	state VARCHAR(255) NOT NULL COMMENT '状态',
	consumed BOOL NOT NULL COMMENT '授权码是否已消费',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_system_oauth2_code_digest UNIQUE (tenant_id, code_digest)
)COMMENT='OAuth2 授权码表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_oauth2_code_tenant ON system_oauth2_code (tenant_id);


-- system_oauth2_refresh_token：OAuth2 刷新令牌
CREATE TABLE system_oauth2_refresh_token (
	user_id BIGINT NOT NULL COMMENT '用户编号',
	token_digest VARCHAR(64) NOT NULL COMMENT '刷新令牌 SHA-256 摘要',
	user_type SMALLINT NOT NULL COMMENT '用户类型（枚举）【UserTypeEnum】',
	client_id VARCHAR(255) NOT NULL COMMENT '客户端编号',
	scopes JSON COMMENT '授权范围 (存储为JSON)',
	expires_time DATETIME NOT NULL COMMENT '过期时间',
	family_id VARCHAR(64) NOT NULL COMMENT '会话族编号',
	credential_revision INTEGER NOT NULL COMMENT '签发时的凭据版本',
	revoked BOOL NOT NULL COMMENT '是否撤销',
	consumed_time DATETIME COMMENT '轮换消费时间，保留记录用于重放检测',
	application_id VARCHAR(64) NOT NULL COMMENT '????',
	domain VARCHAR(64) NOT NULL COMMENT '???',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_system_oauth2_refresh_token_tenant_id UNIQUE (tenant_id, id),
	CONSTRAINT uq_system_oauth2_refresh_token_digest UNIQUE (tenant_id, token_digest)
)COMMENT='OAuth2 刷新令牌' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_oauth2_refresh_token_family ON system_oauth2_refresh_token (tenant_id, family_id);
CREATE INDEX ix_system_oauth2_refresh_token_tenant ON system_oauth2_refresh_token (tenant_id);


-- system_operate_log：操作日志记录
CREATE TABLE system_operate_log (
	trace_id VARCHAR(64) NOT NULL COMMENT '链路追踪编号',
	user_id BIGINT NOT NULL COMMENT '用户编号',
	user_type SMALLINT NOT NULL COMMENT '用户类型（枚举）【UserTypeEnum】',
	type VARCHAR(50) NOT NULL COMMENT '操作模块类型',
	sub_type VARCHAR(50) NOT NULL COMMENT '操作名',
	biz_id BIGINT NOT NULL COMMENT '操作数据模块编号',
	action TEXT NOT NULL COMMENT '操作内容',
	extra TEXT NOT NULL COMMENT '拓展字段',
	request_method VARCHAR(16) NOT NULL COMMENT '请求方法名',
	request_url VARCHAR(255) NOT NULL COMMENT '请求地址',
	user_ip VARCHAR(50) NOT NULL COMMENT '用户 IP',
	user_agent VARCHAR(200) NOT NULL COMMENT '浏览器 UA',
	user_info JSON NOT NULL COMMENT '用户信息 (JSON 格式)',
	event_id VARCHAR(32) COMMENT '审计预留编号',
	result VARCHAR(16) COMMENT 'pending/success/failure/cancelled',
	duration_ms FLOAT COMMENT '操作耗时毫秒',
	lease_until DATETIME COMMENT '审计预留有效期',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)COMMENT='操作日志记录' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_operate_log_tenant ON system_operate_log (tenant_id);


-- system_post：岗位信息表
CREATE TABLE system_post (
	code VARCHAR(64) NOT NULL COMMENT '岗位编码',
	name VARCHAR(50) NOT NULL COMMENT '岗位名称',
	sort INTEGER NOT NULL COMMENT '显示顺序',
	status SMALLINT NOT NULL COMMENT '开启状态（1-启用，0-禁用）【StatusEnum】',
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
	CONSTRAINT uq_system_post_active_0 UNIQUE (tenant_id, code, active_key),
	CONSTRAINT uq_system_post_tenant_id UNIQUE (tenant_id, id)
)COMMENT='岗位信息表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_post_tenant ON system_post (tenant_id);


-- system_role：角色信息表
CREATE TABLE system_role (
	name VARCHAR(30) NOT NULL COMMENT '角色名称',
	code VARCHAR(100) NOT NULL COMMENT '角色权限字符串',
	sort INTEGER NOT NULL COMMENT '显示顺序',
	data_scope SMALLINT NOT NULL COMMENT '数据范围（1：全部数据权限 2：自定数据权限 3：本部门数据权限 4：本部门及以下数据权限 5：本人数据）',
	data_scope_dept_ids JSON NOT NULL COMMENT '数据范围(指定部门数组)',
	builtin SMALLINT NOT NULL COMMENT '内置类型（1-内置 2-自定义）【BuiltinTypeEnum】',
	status SMALLINT NOT NULL COMMENT '开启状态（1-启用，0-禁用）',
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
	CONSTRAINT uq_system_role_active_0 UNIQUE (tenant_id, code, active_key),
	CONSTRAINT uq_system_role_tenant_id UNIQUE (tenant_id, id)
)COMMENT='角色信息表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_role_tenant ON system_role (tenant_id);


-- system_sms_channel：短信渠道信息表
CREATE TABLE system_sms_channel (
	signature VARCHAR(12) NOT NULL COMMENT '短信签名',
	code VARCHAR(63) NOT NULL COMMENT '渠道编码【SmsChannelEnum】',
	status SMALLINT NOT NULL COMMENT '开启状态（1-启用，0-禁用）',
	remark VARCHAR(255) COMMENT '备注',
	api_key VARCHAR(128) NOT NULL COMMENT '短信 API 的账号',
	api_secret VARCHAR(128) COMMENT '短信 API 的秘钥',
	callback_url VARCHAR(255) COMMENT '短信发送回调 URL',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)COMMENT='短信渠道信息表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_sms_channel_tenant ON system_sms_channel (tenant_id);


-- system_sms_code：手机验证码表
CREATE TABLE system_sms_code (
	mobile VARCHAR(11) NOT NULL COMMENT '手机号',
	code VARCHAR(6) NOT NULL COMMENT '验证码',
	create_ip VARCHAR(15) NOT NULL COMMENT '创建 IP',
	scene SMALLINT NOT NULL COMMENT '发送场景',
	today_index SMALLINT NOT NULL COMMENT '今日发送的第几条',
	used BOOL NOT NULL COMMENT '是否使用',
	used_time DATETIME COMMENT '使用时间',
	used_ip VARCHAR(255) COMMENT '使用 IP',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)COMMENT='手机验证码表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_sms_code_tenant ON system_sms_code (tenant_id);


-- system_sms_log：短信日志表
CREATE TABLE system_sms_log (
	channel_id BIGINT NOT NULL COMMENT '短信渠道编号',
	channel_code VARCHAR(63) NOT NULL COMMENT '短信渠道编码',
	template_id BIGINT NOT NULL COMMENT '模板编号',
	template_code VARCHAR(63) NOT NULL COMMENT '模板编码',
	template_type SMALLINT NOT NULL COMMENT '短信类型【SmsTemplateTypeEnum】',
	template_content VARCHAR(255) NOT NULL COMMENT '短信内容',
	template_params JSON NOT NULL COMMENT '短信参数',
	api_template_id VARCHAR(63) COMMENT '短信 API 的模板编号',
	mobile VARCHAR(11) NOT NULL COMMENT '手机号',
	user_id BIGINT COMMENT '用户编号',
	user_type SMALLINT NOT NULL COMMENT '用户类型（枚举）【UserTypeEnum】',
	send_status SMALLINT NOT NULL COMMENT '发送状态',
	send_time DATETIME COMMENT '发送时间',
	api_send_code VARCHAR(63) COMMENT '短信 API 发送结果的编码',
	api_send_msg VARCHAR(255) COMMENT '短信 API 发送失败的提示',
	api_request_id VARCHAR(255) COMMENT '短信 API 发送返回的唯一请求 ID',
	api_serial_no VARCHAR(255) COMMENT '短信 API 发送返回的序号',
	receive_status SMALLINT NOT NULL COMMENT '接收状态',
	receive_time DATETIME COMMENT '接收时间',
	api_receive_code VARCHAR(63) COMMENT 'API 接收结果的编码',
	api_receive_msg VARCHAR(255) COMMENT 'API 接收结果的说明',
	send_claim_token VARCHAR(32) COMMENT '外发 claim 令牌',
	send_claim_until DATETIME COMMENT '外发前 claim 到期时间',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)COMMENT='短信日志表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_sms_log_tenant ON system_sms_log (tenant_id);


-- system_sms_template：短信模板表
CREATE TABLE system_sms_template (
	type SMALLINT NOT NULL COMMENT '短信类型【SmsTemplateTypeEnum】',
	builtin SMALLINT NOT NULL COMMENT '内置类型（1-内置 2-自定义）【BuiltinTypeEnum】',
	status SMALLINT NOT NULL COMMENT '开启状态（1-启用，0-禁用）【StatusEnum】',
	code VARCHAR(63) NOT NULL COMMENT '模板编码',
	name VARCHAR(63) NOT NULL COMMENT '模板名称',
	content VARCHAR(255) NOT NULL COMMENT '模板内容',
	params JSON NOT NULL COMMENT '参数数组',
	remark VARCHAR(255) COMMENT '备注',
	api_template_id VARCHAR(63) NOT NULL COMMENT '短信 API 的模板编号',
	channel_id BIGINT NOT NULL COMMENT '短信渠道编号',
	channel_code VARCHAR(63) NOT NULL COMMENT '短信渠道编码',
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)COMMENT='短信模板表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;


-- system_social_client：社交客户端表
CREATE TABLE system_social_client (
	name VARCHAR(255) NOT NULL COMMENT '应用名',
	social_type SMALLINT NOT NULL COMMENT '社交平台的类型【SocialTypeEnum】',
	user_type SMALLINT NOT NULL COMMENT '用户类型（枚举）【UserTypeEnum】',
	client_id VARCHAR(255) NOT NULL COMMENT '客户端编号',
	client_secret VARCHAR(255) NOT NULL COMMENT '客户端密钥',
	agent_id VARCHAR(255) COMMENT '代理编号',
	auth_config JSON NOT NULL COMMENT '认证配置，JSON格式' DEFAULT ('{}'),
	status SMALLINT NOT NULL COMMENT '开启状态（1-启用，0-禁用）',
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN deleted = 0 THEN 1 ELSE NULL END) COMMENT '仅有效记录参与业务唯一约束',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_system_social_client_active_0 UNIQUE (tenant_id, social_type, user_type, active_key)
)COMMENT='社交客户端表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_social_client_tenant ON system_social_client (tenant_id);


-- system_social_user：社交用户表
CREATE TABLE system_social_user (
	type SMALLINT NOT NULL COMMENT '社交平台的类型【SocialTypeEnum】',
	openid VARCHAR(32) COLLATE utf8mb4_bin NOT NULL COMMENT '社交 openid',
	token VARCHAR(256) COMMENT '社交 token',
	raw_token_info TEXT NOT NULL COMMENT '原始 Token 数据，一般是 JSON 格式',
	nickname VARCHAR(32) NOT NULL COMMENT '用户昵称',
	avatar VARCHAR(255) COMMENT '用户头像',
	raw_user_info TEXT NOT NULL COMMENT '原始用户数据，一般是 JSON 格式',
	code VARCHAR(256) COLLATE utf8mb4_bin NOT NULL COMMENT '最后一次的认证 code',
	state VARCHAR(256) COLLATE utf8mb4_bin COMMENT '最后一次的认证 state',
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN deleted = 0 THEN 1 ELSE NULL END) COMMENT '仅有效记录参与业务唯一约束',
	client_id VARCHAR(255) NOT NULL COMMENT '第三方应用编号',
	subject_type VARCHAR(32) NOT NULL COMMENT '第三方主体类型',
	application_id VARCHAR(64) NOT NULL COMMENT '本站社交应用标识',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_system_social_user_active_0 UNIQUE (tenant_id, type, openid, client_id, subject_type, application_id, active_key),
	CONSTRAINT uq_system_social_user_tenant_id UNIQUE (tenant_id, id)
)COMMENT='社交用户表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_social_user_tenant ON system_social_user (tenant_id);


-- system_tenant：租户
CREATE TABLE system_tenant (
	name VARCHAR(30) NOT NULL COMMENT '租户名',
	contact_user_id BIGINT COMMENT '联系人的用户编号',
	contact_name VARCHAR(30) NOT NULL COMMENT '联系人',
	contact_mobile VARCHAR(50) COMMENT '联系手机',
	status SMALLINT NOT NULL COMMENT '开启状态（1-启用，0-禁用）',
	websites JSON COMMENT '绑定域名列表',
	package_id BIGINT NOT NULL COMMENT '租户套餐编号',
	expire_time DATETIME COMMENT '过期时间',
	account_count BIGINT NOT NULL COMMENT '账号数量',
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)COMMENT='租户' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;


-- system_tenant_package：租户套餐
CREATE TABLE system_tenant_package (
	name VARCHAR(30) NOT NULL COMMENT '套餐名',
	status SMALLINT NOT NULL COMMENT '开启状态（1-启用，0-禁用）',
	remark VARCHAR(256) COMMENT '备注',
	menu_ids JSON NOT NULL COMMENT '关联的菜单编号 (JSON)',
	quota_config JSON COMMENT '通用配额模板（多模块共享，如 ai / sms / storage）',
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id)
)COMMENT='租户套餐' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;


-- system_oauth2_access_token：OAuth2 访问令牌
CREATE TABLE system_oauth2_access_token (
	user_id BIGINT NOT NULL COMMENT '用户编号',
	user_type SMALLINT NOT NULL COMMENT '用户类型（枚举）【UserTypeEnum】',
	user_info JSON NOT NULL COMMENT '用户信息 (JSON 格式)',
	scopes JSON COMMENT '授权范围 (JSON 数组格式)',
	token_digest VARCHAR(64) NOT NULL COMMENT '访问令牌 SHA-256 摘要',
	refresh_token_id BIGINT COMMENT '刷新令牌记录编号',
	client_id VARCHAR(255) NOT NULL COMMENT '客户端编号',
	expires_time DATETIME NOT NULL COMMENT '过期时间',
	family_id VARCHAR(64) NOT NULL COMMENT '会话族编号',
	credential_revision INTEGER NOT NULL COMMENT '签发时的凭据版本',
	revoked BOOL NOT NULL COMMENT '是否撤销',
	application_id VARCHAR(64) NOT NULL COMMENT '????',
	domain VARCHAR(64) NOT NULL COMMENT '???',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT fk_system_oauth2_access_token_refresh_token_id FOREIGN KEY(tenant_id, refresh_token_id) REFERENCES system_oauth2_refresh_token (tenant_id, id),
	CONSTRAINT uq_system_oauth2_access_token_digest UNIQUE (tenant_id, token_digest)
)COMMENT='OAuth2 访问令牌' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_oauth2_access_token_family ON system_oauth2_access_token (tenant_id, family_id);
CREATE INDEX ix_system_oauth2_access_token_tenant ON system_oauth2_access_token (tenant_id);


-- system_role_menu：角色和菜单关联表
CREATE TABLE system_role_menu (
	role_id BIGINT NOT NULL COMMENT '角色ID',
	menu_id BIGINT NOT NULL COMMENT '菜单ID',
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN deleted = 0 THEN 1 ELSE NULL END) COMMENT '仅有效记录参与业务唯一约束',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_system_role_menu_active_0 UNIQUE (tenant_id, role_id, menu_id, active_key),
	CONSTRAINT fk_system_role_menu_role_id FOREIGN KEY(tenant_id, role_id) REFERENCES system_role (tenant_id, id)
)COMMENT='角色和菜单关联表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_role_menu_tenant ON system_role_menu (tenant_id);


-- system_social_user_bind：社交绑定表
CREATE TABLE system_social_user_bind (
	user_id BIGINT NOT NULL COMMENT '用户编号',
	user_type SMALLINT NOT NULL COMMENT '用户类型（枚举）【UserTypeEnum】',
	social_type SMALLINT NOT NULL COMMENT '社交平台的类型【SocialTypeEnum】',
	social_user_id BIGINT NOT NULL COMMENT '社交用户的编号',
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN deleted = 0 THEN 1 ELSE NULL END) COMMENT '仅有效记录参与业务唯一约束',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_system_social_user_bind_active_0 UNIQUE (tenant_id, user_type, social_type, social_user_id, active_key),
	CONSTRAINT uq_system_social_user_bind_active_1 UNIQUE (tenant_id, user_type, social_type, user_id, active_key),
	CONSTRAINT fk_system_social_user_bind_social_user_id FOREIGN KEY(tenant_id, social_user_id) REFERENCES system_social_user (tenant_id, id)
)COMMENT='社交绑定表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_social_user_bind_tenant ON system_social_user_bind (tenant_id);


-- system_users：用户信息表
CREATE TABLE system_users (
	username VARCHAR(30) NOT NULL COMMENT '用户账号',
	password VARCHAR(100) NOT NULL COMMENT '密码',
	nickname VARCHAR(30) COMMENT '用户昵称',
	remark VARCHAR(500) COMMENT '备注',
	dept_id BIGINT COMMENT '部门ID',
	post_ids JSON COMMENT '岗位编号列表（JSON 格式）',
	email VARCHAR(50) COMMENT '用户邮箱',
	mobile VARCHAR(11) COMMENT '手机号码',
	sex SMALLINT COMMENT '用户性别',
	avatar VARCHAR(512) COMMENT '头像地址',
	status SMALLINT NOT NULL COMMENT '开启状态（1-启用，0-禁用）',
	login_ip VARCHAR(50) COMMENT '最后登录IP',
	login_date DATETIME COMMENT '最后登录时间',
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN deleted = 0 THEN 1 ELSE NULL END) COMMENT '仅有效记录参与业务唯一约束',
	credential_revision INTEGER NOT NULL COMMENT '凭据版本，改密或账号状态变化时递增',
	authorization_revision INTEGER NOT NULL COMMENT '权限版本，与授权变化原子提交',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_system_users_active_0 UNIQUE (tenant_id, username, active_key),
	CONSTRAINT uq_system_users_tenant_id UNIQUE (tenant_id, id),
	CONSTRAINT fk_system_users_dept_id FOREIGN KEY(tenant_id, dept_id) REFERENCES system_dept (tenant_id, id)
)COMMENT='用户信息表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_users_tenant ON system_users (tenant_id);


-- system_user_post：用户岗位表
CREATE TABLE system_user_post (
	user_id BIGINT NOT NULL COMMENT '用户ID',
	post_id BIGINT NOT NULL COMMENT '岗位ID',
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN deleted = 0 THEN 1 ELSE NULL END) COMMENT '仅有效记录参与业务唯一约束',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_system_user_post_active_0 UNIQUE (tenant_id, user_id, post_id, active_key),
	CONSTRAINT fk_system_user_post_user_id FOREIGN KEY(tenant_id, user_id) REFERENCES system_users (tenant_id, id),
	CONSTRAINT fk_system_user_post_post_id FOREIGN KEY(tenant_id, post_id) REFERENCES system_post (tenant_id, id)
)COMMENT='用户岗位表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_user_post_tenant ON system_user_post (tenant_id);


-- system_user_profiles：用户详情表
CREATE TABLE system_user_profiles (
	user_id BIGINT NOT NULL COMMENT '用户ID',
	bio VARCHAR(500) COMMENT '个人简介',
	tags JSON COMMENT '用户标签',
	address VARCHAR(255) COMMENT '地址',
	skills JSON COMMENT '技能标签',
	work_scope VARCHAR(500) COMMENT '工作职责描述',
	expertise VARCHAR(500) COMMENT '专业领域',
	communication_style VARCHAR(50) COMMENT '沟通风格（formal/casual/technical）',
	ai_preference JSON COMMENT 'AI 交互偏好（用户主动设置）',
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN deleted = 0 THEN 1 ELSE NULL END) COMMENT '仅有效记录参与业务唯一约束',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_system_user_profiles_active_0 UNIQUE (tenant_id, user_id, active_key),
	CONSTRAINT fk_system_user_profiles_user_id FOREIGN KEY(tenant_id, user_id) REFERENCES system_users (tenant_id, id)
)COMMENT='用户详情表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_user_profiles_tenant ON system_user_profiles (tenant_id);
CREATE INDEX ix_system_user_profiles_user_id ON system_user_profiles (user_id);


-- system_user_role：用户角色关联表
CREATE TABLE system_user_role (
	user_id BIGINT NOT NULL COMMENT '用户ID',
	role_id BIGINT NOT NULL COMMENT '角色ID',
	active_key SMALLINT GENERATED ALWAYS AS (CASE WHEN deleted = 0 THEN 1 ELSE NULL END) COMMENT '仅有效记录参与业务唯一约束',
	tenant_id VARCHAR(32) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	creator VARCHAR(64) NOT NULL,
	create_time DATETIME NOT NULL,
	updater VARCHAR(64) NOT NULL,
	update_time DATETIME NOT NULL,
	deleted BOOL NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_system_user_role_active_0 UNIQUE (tenant_id, user_id, role_id, active_key),
	CONSTRAINT fk_system_user_role_user_id FOREIGN KEY(tenant_id, user_id) REFERENCES system_users (tenant_id, id),
	CONSTRAINT fk_system_user_role_role_id FOREIGN KEY(tenant_id, role_id) REFERENCES system_role (tenant_id, id)
)COMMENT='用户角色关联表' ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE INDEX ix_system_user_role_tenant ON system_user_role (tenant_id);
