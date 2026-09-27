import type { DataSourceUrlConfig } from './typing';

import { InfraDbTypeEnum } from '#/constants/enums';

export const databaseTypes = Object.values(InfraDbTypeEnum);

export function getDatabaseType(value: string) {
  return databaseTypes.find((item) => item.value === value);
}

export function parseDatabaseUrl(
  value: string,
  preferredType: string,
): DataSourceUrlConfig {
  const separator = value.indexOf('://');
  const protocol = value.slice(0, separator);
  const preferred = getDatabaseType(preferredType);
  const database =
    preferred?.protocol === protocol
      ? preferred
      : databaseTypes.find((item) => item.protocol === protocol);
  if (separator < 1 || !database) throw new Error('不支持的数据库连接协议');

  // dm+dushan_async 包含下划线，不能直接作为浏览器 URL 的 scheme。
  const parsed = new URL(`database://${value.slice(separator + 3)}`);
  if (!parsed.hostname) throw new Error('请输入数据库主机地址');
  return {
    database: parsed.pathname.slice(1),
    dbType: database.value,
    host: parsed.hostname,
    password: decodeURIComponent(parsed.password),
    port: parsed.port ? Number(parsed.port) : undefined,
    query: parsed.search,
    username: decodeURIComponent(parsed.username),
  };
}

export function buildDatabaseUrl(config: DataSourceUrlConfig) {
  const database = getDatabaseType(config.dbType);
  if (!database?.enabled) throw new Error('该数据库类型尚未启用');
  const host =
    config.host.includes(':') && !config.host.startsWith('[')
      ? `[${config.host}]`
      : config.host;
  const port = config.port === undefined ? '' : `:${config.port}`;
  return `${database.protocol}://${encodeURIComponent(config.username)}:${encodeURIComponent(config.password)}@${host}${port}/${config.database}${config.query}`;
}

export function isDatabaseUrlForType(value: string, dbType: string) {
  try {
    return (
      getDatabaseType(dbType)?.enabled === true &&
      parseDatabaseUrl(value, dbType).dbType === dbType
    );
  } catch {
    return false;
  }
}
