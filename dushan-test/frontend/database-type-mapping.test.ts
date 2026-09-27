import { describe, expect, it } from 'vitest';

import { InfraDbTypeEnum } from '../../dushan-admin-frontend/apps/web-ele/src/constants/enums';
import {
  buildDatabaseUrl,
  isDatabaseUrlForType,
  parseDatabaseUrl,
} from '../../dushan-admin-frontend/apps/web-ele/src/components/data-source-url/url';

describe('数据库类型使用已确认的后端连接协议', () => {
  it.each([
    ['mysql', 'mysql+aiomysql', 3306],
    ['postgresql', 'postgresql+asyncpg', 5432],
    ['dm', 'dm+dushan_async', 5236],
    ['opengauss', 'opengauss+asyncpg', 5432],
    ['kingbase', 'kingbase+asyncpg', 54321],
    ['oceanbase', 'oceanbase+aiomysql', 2881],
    ['tidb', 'mysql+aiomysql', 4000],
  ] as const)(
    '%s生成和解析%s，保留独立数据库类型',
    (dbType, protocol, port) => {
      const config = {
        dbType,
        host: 'db.internal',
        port,
        database: 'demo',
        username: 'user@site',
        password: 'p@:/#%',
        query: '?connect_timeout=7',
      };
      const url = buildDatabaseUrl(config);
      expect(url).toBe(
        `${protocol}://user%40site:p%40%3A%2F%23%25@db.internal:${port}/demo?connect_timeout=7`,
      );
      expect(parseDatabaseUrl(url, dbType)).toEqual(config);
      expect(isDatabaseUrlForType(url, dbType)).toBe(true);
    },
  );

  it('TiDB未指定端口时不会因回填或编辑其他字段被补上4000', () => {
    const url = 'mysql+aiomysql://user:pass@db/demo?charset=utf8mb4';
    const parsed = parseDatabaseUrl(url, 'tidb');
    expect(parsed.dbType).toBe('tidb');
    expect(parsed.port).toBeUndefined();
    expect(buildDatabaseUrl(parsed)).toBe(url);
    expect(parseDatabaseUrl(url, 'mysql').dbType).toBe('mysql');
  });

  it('拒绝旧错误驱动、未知协议和与类型不符的URL', () => {
    expect(isDatabaseUrlForType('dm+aioodbc://a:b@db/demo', 'dm')).toBe(false);
    expect(
      isDatabaseUrlForType('gaussdb+asyncpg://a:b@db/demo', 'opengauss'),
    ).toBe(false);
    expect(isDatabaseUrlForType('tidb+aiomysql://a:b@db/demo', 'tidb')).toBe(
      false,
    );
    expect(
      isDatabaseUrlForType('postgresql+asyncpg://a:b@db/demo', 'mysql'),
    ).toBe(false);
    expect(isDatabaseUrlForType('mysql+aiomysql://', 'mysql')).toBe(false);
  });

  it('Oracle和SQLServer未启用，不生成或接受新连接配置', () => {
    expect(InfraDbTypeEnum.ORACLE.enabled).toBe(false);
    expect(InfraDbTypeEnum.MSSQL.enabled).toBe(false);
    for (const database of [InfraDbTypeEnum.ORACLE, InfraDbTypeEnum.MSSQL]) {
      expect(
        isDatabaseUrlForType(
          `${database.protocol}://a:b@db/demo`,
          database.value,
        ),
      ).toBe(false);
      expect(() =>
        buildDatabaseUrl({
          dbType: database.value,
          host: 'db',
          port: database.port,
          username: 'a',
          password: 'b',
          database: 'demo',
          query: '',
        }),
      ).toThrow();
    }
  });
});
