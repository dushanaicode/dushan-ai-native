import type { PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 缓存管理端点（`/infra/cache/monitor`）。 */
export namespace InfraRedisCacheApi {
  /** 缓存信息 RespVO */
  export interface CacheInfoRespVO {
    cacheKey?: string;
    cacheName?: string;
    cacheValue?: unknown;
  }

  /** Redis DB 信息 */
  export interface CacheDbInfoRespVO {
    dbIndex: number;
    keyCount?: number;
    label: string;
    name: string;
  }

  /** 缓存键详情 */
  export interface CacheKeyDetailRespVO {
    dbName: string;
    key: string;
    keyType: string;
    size?: number;
    ttl: number;
    value?: string;
  }
}

/** 获得所有缓存名称 */
export async function getCacheNames(params: PageParam) {
  return requestClient.get<PageResult<InfraRedisCacheApi.CacheInfoRespVO>>(
    '/infra/cache/monitor/get-names',
    { params },
  );
}

/** 获得指定缓存名称下的键列表 */
export async function getCacheKeys(params: PageParam & { keyPrefix: string }) {
  return requestClient.get<PageResult<string>>(
    '/infra/cache/monitor/get-keys',
    { params },
  );
}

/** 获得指定缓存键的值 */
export async function getCacheValue(keyPrefix: string, cacheKey: string) {
  return requestClient.get<InfraRedisCacheApi.CacheInfoRespVO>(
    '/infra/cache/monitor/get-value',
    { params: { cacheKey, keyPrefix } },
  );
}

/** 清除指定缓存名称下的所有缓存 */
export async function clearCacheByName(keyPrefix: string) {
  return requestClient.delete('/infra/cache/monitor/clear-cache-name', {
    params: { keyPrefix },
  });
}

/** 清除匹配模式的缓存键 */
export async function clearCacheByKey(cacheKeyPattern: string) {
  return requestClient.delete('/infra/cache/monitor/clear-cache-key', {
    params: { cacheKeyPattern },
  });
}

/** 清除所有缓存(FLUSHDB) */
export async function clearAllCaches() {
  return requestClient.delete('/infra/cache/monitor/clear-cache-all');
}

/** 获取所有配置的 Redis DB 列表 */
export async function getDbList() {
  return requestClient.get<InfraRedisCacheApi.CacheDbInfoRespVO[]>(
    '/infra/cache/monitor/db-list',
  );
}

/** 扫描指定 DB 中的所有 key */
export async function scanDbKeys(dbName: string, pattern = '*') {
  return requestClient.get<string[]>('/infra/cache/monitor/db-keys', {
    params: { dbName, pattern },
  });
}

/** 获取指定 key 的详细信息 */
export async function getKeyDetail(dbName: string, key: string) {
  return requestClient.get<InfraRedisCacheApi.CacheKeyDetailRespVO>(
    '/infra/cache/monitor/key-detail',
    { params: { dbName, key } },
  );
}

/** 删除指定 DB 中的单个 key */
export async function deleteKey(dbName: string, key: string) {
  return requestClient.delete('/infra/cache/monitor/delete-key', {
    params: { dbName, key },
  });
}
