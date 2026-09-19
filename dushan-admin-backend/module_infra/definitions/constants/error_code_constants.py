from framework.common.exception import ErrorCode, error_code


@error_code
class ErrorCodeConstants:
    """
    Infra 错误码枚举类

    infra 系统，使用 1-001-000-000 段
    """

    JOB_NOT_EXISTS = ErrorCode(
        code=1001001000, description="定时任务不存在", message_key="infra.job.not_exists"
    )
    JOB_HANDLER_EXISTS = ErrorCode(
        code=1001001001,
        description="定时任务的处理器已经存在",
        message_key="infra.job.handler_exists",
    )
    JOB_CHANGE_STATUS_INVALID = ErrorCode(
        code=1001001002,
        description="只允许修改为开启或者关闭状态",
        message_key="infra.job.change_status_invalid",
    )
    JOB_CHANGE_STATUS_EQUALS = ErrorCode(
        code=1001001003,
        description="定时任务已经处于该状态，无需修改",
        message_key="infra.job.change_status_equals",
    )
    JOB_UPDATE_ONLY_NORMAL_STATUS = ErrorCode(
        code=1001001004,
        description="只有开启状态的任务，才可以修改",
        message_key="infra.job.update_only_normal_status",
    )
    JOB_CRON_EXPRESSION_VALID = ErrorCode(
        code=1001001005,
        description="CRON 表达式不正确",
        message_key="infra.job.cron_expression_valid",
    )
    JOB_HANDLER_BEAN_NOT_EXISTS = ErrorCode(
        code=1001001006,
        description="定时任务的处理器 Bean 不存在",
        message_key="infra.job.handler_bean_not_exists",
    )
    JOB_HANDLER_BEAN_TYPE_ERROR = ErrorCode(
        code=1001001007,
        description="定时任务的处理器 Bean 类型不正确",
        message_key="infra.job.handler_bean_type_error",
    )
    JOB_UPDATE_FAIL = ErrorCode(
        code=1001001008, description="更新调度器任务失败", message_key="infra.job.update_fail"
    )
    JOB_STATUS_UPDATE_FAIL = ErrorCode(
        code=1001001009,
        description="更新调度器任务状态失败",
        message_key="infra.job.status_update_fail",
    )
    JOB_TRIGGER_FAIL = ErrorCode(
        code=1001001010, description="手动触发任务执行失败", message_key="infra.job.trigger_fail"
    )
    JOB_SYNC_FAIL_SCHEDULER = ErrorCode(
        code=1001001011,
        description="无法获取调度器任务列表",
        message_key="infra.job.sync_fail_scheduler",
    )
    API_ERROR_LOG_NOT_FOUND = ErrorCode(
        code=1001002000,
        description="API 错误日志不存在",
        message_key="infra.log.error_log_not_found",
    )
    API_ERROR_LOG_PROCESSED = ErrorCode(
        code=1001002001,
        description="API 错误日志已处理",
        message_key="infra.log.error_log_processed",
    )
    FILE_PATH_EXISTS = ErrorCode(
        code=1001003000, description="文件路径已存在", message_key="infra.file.path_exists"
    )
    FILE_NOT_EXISTS = ErrorCode(
        code=1001003001, description="文件不存在", message_key="infra.file.not_exists"
    )
    FILE_IS_EMPTY = ErrorCode(
        code=1001003002, description="文件为空", message_key="infra.file.is_empty"
    )
    FILE_NODE_NOT_EXISTS = ErrorCode(
        code=1001004000, description="文件节点不存在", message_key="infra.file.node_not_exists"
    )
    FILE_NODE_ALREADY_EXISTS = ErrorCode(
        code=1001004001,
        description="同名文件节点已存在",
        message_key="infra.file.node_already_exists",
    )
    FILE_NODE_PARENT_NOT_EXISTS = ErrorCode(
        code=1001004002, description="父节点不存在", message_key="infra.file.node_parent_not_exists"
    )
    FILE_NODE_PARENT_NOT_FOLDER = ErrorCode(
        code=1001004003,
        description="父节点不是文件夹",
        message_key="infra.file.node_parent_not_folder",
    )
    FILE_NODE_CANNOT_MOVE_TO_CHILD = ErrorCode(
        code=1001004004,
        description="不能将节点移动到其子节点下",
        message_key="infra.file.node_cannot_move_to_child",
    )
    FILE_CONFIG_DATA_NOT_EXISTS = ErrorCode(
        code=1001005000, description="文件配置不存在", message_key="infra.file.config_not_exists"
    )
    FILE_CONFIG_DELETE_FAIL_MASTER = ErrorCode(
        code=1001005001,
        description="该文件配置不允许删除，原因：它是主配置",
        message_key="infra.file.config_delete_fail_master",
    )
    FILE_CONFIG_HAS_FILE = ErrorCode(
        code=1001005002,
        description="该配置下存在文件，无法删除",
        message_key="infra.file.config_has_file",
    )
    CACHE_GET_MONITOR_INFO_ERROR = ErrorCode(
        code=1001006000,
        description="获取缓存监控信息失败",
        message_key="infra.cache.get_monitor_info_error",
    )
    CACHE_DELETE_FAILED = ErrorCode(
        code=1001006001, description="删除缓存信息失败", message_key="infra.cache.delete_failed"
    )
    CACHE_FLUSHDB_FAILED = ErrorCode(
        code=1001006002,
        description="清除缓存当前数据库中的所有数据失败",
        message_key="infra.cache.flushdb_failed",
    )
    MQ_DEFINITION_NOT_EXISTS = ErrorCode(
        code=1001007000,
        description="MQ 消息定义不存在",
        message_key="infra.mq.definition_not_exists",
    )
    MQ_DEFINITION_TOPIC_EXISTS = ErrorCode(
        code=1001007001,
        description="MQ Topic 已被其它定义使用",
        message_key="infra.mq.definition_topic_exists",
    )
    MQ_DEFINITION_CONSUMER_EXISTS = ErrorCode(
        code=1001007002,
        description="MQ 消费者已被其它定义使用",
        message_key="infra.mq.definition_consumer_exists",
    )
    MQ_DEFINITION_CHANGE_STATUS_INVALID = ErrorCode(
        code=1001007003,
        description="只允许修改为开启或者暂停状态",
        message_key="infra.mq.definition_change_status_invalid",
    )
    MQ_DEFINITION_CHANGE_STATUS_EQUALS = ErrorCode(
        code=1001007004,
        description="MQ 消息定义已经处于该状态，无需修改",
        message_key="infra.mq.definition_change_status_equals",
    )
    MQ_MESSAGE_NOT_EXISTS = ErrorCode(
        code=1001008000, description="MQ 消息实例不存在", message_key="infra.mq.message_not_exists"
    )
    MQ_MESSAGE_RESEND_FAIL_STATUS_WRONG = ErrorCode(
        code=1001008001,
        description="重发消息失败，只有失败或等待中的消息才能重发",
        message_key="infra.mq.message_resend_fail_status_wrong",
    )
    DATA_SOURCE_CONFIG_DATA_NOT_EXISTS = ErrorCode(
        code=1001009000, description="数据源配置不存在", message_key="infra.data_source.not_exists"
    )
    DATA_SOURCE_CONFIG_NAME_DUPLICATE = ErrorCode(
        code=1001009001,
        description="已经存在名为【{}】的数据源",
        message_key="infra.data_source.name_duplicate",
    )
    DATA_SOURCE_CONFIG_TEST_FAILED = ErrorCode(
        code=1001009002,
        description="数据源连接测试失败：{}",
        message_key="infra.data_source.test_failed",
    )
    DATA_SOURCE_CONFIG_DELETE_DEFAULT = ErrorCode(
        code=1001009003,
        description="不能删除默认数据源",
        message_key="infra.data_source.delete_default",
    )
    DATA_SOURCE_CONFIG_ACTIVATE_FAILED = ErrorCode(
        code=1001009004,
        description="激活数据源失败：{}",
        message_key="infra.data_source.activate_failed",
    )
    CONFIG_DATA_NOT_EXISTS = ErrorCode(
        code=1001010000, description="参数配置不存在", message_key="infra.config.data_not_exists"
    )
    CONFIG_DATA_KEY_DUPLICATE = ErrorCode(
        code=1001010001,
        description="参数配置 key 重复",
        message_key="infra.config.data_key_duplicate",
    )
    CONFIG_DATA_CAN_NOT_DELETE_SYSTEM_TYPE = ErrorCode(
        code=1001010002,
        description="不能删除类型为系统内置的参数配置",
        message_key="infra.config.can_not_delete_system_type",
    )
    CONFIG_DATA_GET_VALUE_ERROR_IF_VISIBLE = ErrorCode(
        code=1001010003,
        description="获取参数配置失败，原因：不允许获取不可见配置",
        message_key="infra.config.get_value_error_if_visible",
    )
    CONFIG_TYPE_NOT_EXISTS = ErrorCode(
        code=1001010004, description="配置类型不存在", message_key="infra.config.type_not_exists"
    )
    CONFIG_TYPE_NAME_DUPLICATE = ErrorCode(
        code=1001010005,
        description="配置类型名称已存在",
        message_key="infra.config.type_name_duplicate",
    )
    CONFIG_TYPE_CODE_DUPLICATE = ErrorCode(
        code=1001010006,
        description="配置类型编码已存在",
        message_key="infra.config.type_code_duplicate",
    )
    CONFIG_TYPE_HAS_CHILDREN = ErrorCode(
        code=1001010007,
        description="配置类型下存在配置数据，无法删除",
        message_key="infra.config.type_has_children",
    )
    CONFIG_TYPE_NOT_ENABLE = ErrorCode(
        code=1001010008,
        description="配置类型不处于开启状态，不允许选择",
        message_key="infra.config.type_not_enable",
    )
    CODEGEN_TABLE_NOT_EXISTS = ErrorCode(
        code=1001011000,
        description="代码生成表定义不存在",
        message_key="infra.codegen.table_not_exists",
    )
    CODEGEN_IMPORT_TABLE_EXISTS = ErrorCode(
        code=1001011001,
        description="导入的表已存在",
        message_key="infra.codegen.import_table_exists",
    )
    CODEGEN_COLUMN_NOT_EXISTS = ErrorCode(
        code=1001011002,
        description="代码生成字段定义不存在",
        message_key="infra.codegen.column_not_exists",
    )
    CODEGEN_SYNC_NONE_CHANGE = ErrorCode(
        code=1001011003,
        description="同步失败，表结构无变化",
        message_key="infra.codegen.sync_none_change",
    )
    CODEGEN_IMPORT_COLUMNS_NULL = ErrorCode(
        code=1001011004,
        description="导入失败，表中无字段",
        message_key="infra.codegen.import_columns_null",
    )
    CODEGEN_TABLE_INFO_TABLE_COMMENT_IS_NULL = ErrorCode(
        code=1001011005,
        description="数据库表的描述为空",
        message_key="infra.codegen.table_comment_is_null",
    )
    CODEGEN_SYNC_COLUMNS_NULL = ErrorCode(
        code=1001011006,
        description="同步失败，数据库中该表已无字段",
        message_key="infra.codegen.sync_columns_null",
    )
