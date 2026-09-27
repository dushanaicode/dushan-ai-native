/**
 * 业务枚举常量，与后端 framework/common/enums 及
 * 各 module definitions/enums 的取值一一对应。
 */

/** 通用内置类型（common_builtin_type 字典） */
export const CommonBuiltinTypeEnum = {
  BUILTIN: 1,
  CUSTOM: 2,
} as const;

/** 用户类型（UserTypeEnum） */
export const UserTypeEnum = {
  MEMBER: 1,
  ADMIN: 2,
  CLIENT: 3,
} as const;

/** 社交平台类型（SocialTypeEnum / system_social_type 字典） */
export const SystemUserSocialTypeEnum = {
  ALIPAY: {
    img: 'https://s21.ax1x.com/2025/07/22/pVGiMq0.png',
    source: 'alipay',
    title: '支付宝',
    type: 10,
  },
  DINGTALK: {
    img: 'https://s21.ax1x.com/2025/07/22/pVGiFVf.png',
    source: 'dingtalk',
    title: '钉钉',
    type: 20,
  },
  WECHAT_ENTERPRISE: {
    img: 'https://s21.ax1x.com/2025/07/22/pVGiVPg.png',
    source: 'wechat_enterprise',
    title: '企业微信',
    type: 30,
  },
  WECHAT_MP: {
    img: 'https://s21.ax1x.com/2025/07/22/pVGiYRJ.png',
    source: 'wechat_mp',
    title: '微信公众号',
    type: 31,
  },
  WECHAT_OPEN: {
    img: 'https://s21.ax1x.com/2025/07/22/pVGiKrq.png',
    source: 'wechat_open',
    title: '微信开放平台',
    type: 32,
  },
  WECHAT_MINI_PROGRAM: {
    img: 'https://s21.ax1x.com/2025/07/22/pVGimxs.png',
    source: 'wechat_mini_program',
    title: '微信小程序',
    type: 33,
  },
  WECHAT_ENTERPRISE_v2: {
    img: 'https://s21.ax1x.com/2025/07/22/pVGiVPg.png',
    source: 'wechat_enterprise_v2',
    title: '企业微信V2',
    type: 34,
  },
} as const;

/** 代码生成模板类型（CodegenTemplateTypeEnum / infra_codegen_template_type） */
export const InfraCodegenTemplateTypeEnum = {
  CRUD: 1,
  TREE: 2,
  SUB: 15,
} as const;

/** 任务状态（JobStatusEnum / infra_job_status） */
export const InfraJobStatusEnum = {
  INIT: 0,
  NORMAL: 1,
  STOP: 2,
} as const;

/** API 错误日志处理状态（infra_api_error_log_process_status） */
export const InfraApiErrorLogProcessStatusEnum = {
  INIT: 0,
  DONE: 1,
  IGNORE: 2,
} as const;

/** 数据库类型与 Native 异步连接协议；TiDB 共用 MySQL 协议。 */
export const InfraDbTypeEnum = {
  MYSQL: {
    label: 'MySQL/MariaDB',
    value: 'mysql',
    protocol: 'mysql+aiomysql',
    port: 3306,
    enabled: true,
  },
  POSTGRESQL: {
    label: 'PostgreSQL',
    value: 'postgresql',
    protocol: 'postgresql+asyncpg',
    port: 5432,
    enabled: true,
  },
  DM: {
    label: '达梦数据库 (DM Database)',
    value: 'dm',
    protocol: 'dm+dushan_async',
    port: 5236,
    enabled: true,
  },
  OPENGAUSS: {
    label: 'openGauss',
    value: 'opengauss',
    protocol: 'opengauss+asyncpg',
    port: 5432,
    enabled: true,
  },
  KINGBASE: {
    label: '人大金仓 (PostgreSQL 模式)',
    value: 'kingbase',
    protocol: 'kingbase+asyncpg',
    port: 54_321,
    enabled: true,
  },
  OCEANBASE: {
    label: 'OceanBase (MySQL 模式)',
    value: 'oceanbase',
    protocol: 'oceanbase+aiomysql',
    port: 2881,
    enabled: true,
  },
  TIDB: {
    label: 'TiDB',
    value: 'tidb',
    protocol: 'mysql+aiomysql',
    port: 4000,
    enabled: true,
  },
  MSSQL: {
    label: 'Microsoft SQL Server',
    value: 'mssql',
    protocol: 'mssql+aioodbc',
    port: 1433,
    enabled: false,
  },
  ORACLE: {
    label: 'Oracle Database',
    value: 'oracle',
    protocol: 'oracle+oracledb',
    port: 1521,
    enabled: false,
  },
} as const;
