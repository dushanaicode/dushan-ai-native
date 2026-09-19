/**
 * 字典类型常量，与后端 `sql/mysql/**` 种子的 `system_dict_type.type` 一一对应。
 * 页面渲染枚举字段用 `<DictTag :type="DICT_TYPE.X" :value="row.y" />`；
 * 表单选项用 `dictionary.getDictOptions(DICT_TYPE.X, valueType)`。
 * 字典 value 均为字符串，valueType 按需要 'number' | 'string' | 'boolean' 转换。
 */
export const DICT_TYPE = {
  COMMON_BUILTIN_TYPE: 'common_builtin_type',
  COMMON_PERMISSION_TYPE: 'common_permission_type',
  COMMON_STATUS: 'common_status',
  INFRA_API_ERROR_LOG_PROCESS_STATUS: 'infra_api_error_log_process_status',
  INFRA_BOOLEAN_STRING: 'infra_boolean_string',
  INFRA_CODEGEN_FRONT_TYPE: 'infra_codegen_front_type',
  INFRA_CODEGEN_SCENE: 'infra_codegen_scene',
  INFRA_CODEGEN_TEMPLATE_TYPE: 'infra_codegen_template_type',
  INFRA_CONFIG_MODULE: 'infra_config_module',
  INFRA_CONFIG_TYPE: 'infra_config_type',
  INFRA_DATA_SOURCE_HEALTH_STATUS: 'infra_data_source_health_status',
  INFRA_DATA_SOURCE_TYPE: 'infra_data_source_type',
  INFRA_FILE_STORAGE: 'infra_file_storage',
  INFRA_JOB_LOG_STATUS: 'infra_job_log_status',
  INFRA_JOB_STATUS: 'infra_job_status',
  INFRA_LOAD_BALANCER_STRATEGY: 'infra_load_balancer_strategy',
  INFRA_MQ_LOG_STATUS: 'infra_mq_log_status',
  INFRA_OPERATE_TYPE: 'infra_operate_type',
  SYSTEM_ANNOUNCEMENT_CATEGORY: 'system_announcement_category',
  SYSTEM_ANNOUNCEMENT_STATUS: 'system_announcement_status',
  SYSTEM_DATA_SCOPE: 'system_data_scope',
  SYSTEM_LOGIN_RESULT: 'system_login_result',
  SYSTEM_LOGIN_TYPE: 'system_login_type',
  SYSTEM_MAIL_SEND_STATUS: 'system_mail_send_status',
  SYSTEM_MENU_TYPE: 'system_menu_type',
  SYSTEM_NOTICE_PUSH_STATUS: 'system_notice_push_status',
  SYSTEM_NOTICE_TYPE: 'system_notice_type',
  SYSTEM_NOTIFICATION_CHANNEL: 'system_notification_channel',
  SYSTEM_OAUTH2_GRANT_TYPE: 'system_oauth2_grant_type',
  SYSTEM_PUSH_TARGET_TYPE: 'system_push_target_type',
  SYSTEM_SMS_CHANNEL_CODE: 'system_sms_channel_code',
  SYSTEM_SMS_RECEIVE_STATUS: 'system_sms_receive_status',
  SYSTEM_SMS_SEND_STATUS: 'system_sms_send_status',
  SYSTEM_SMS_TEMPLATE_TYPE: 'system_sms_template_type',
  SYSTEM_SOCIAL_TYPE: 'system_social_type',
  SYSTEM_USER_SEX: 'system_user_sex',
  USER_TYPE: 'user_type',
} as const;

export type DictTypeValue = (typeof DICT_TYPE)[keyof typeof DICT_TYPE];
