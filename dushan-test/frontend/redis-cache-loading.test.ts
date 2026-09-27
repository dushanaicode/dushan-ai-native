import { afterEach, expect, it, vi } from 'vitest';
import { createApp, h } from 'vue';

import { useRedisCache } from '../../dushan-admin-frontend/apps/web-ele/src/views/infra/redis-cache/composables/use-redis-cache';

const api = vi.hoisted(() => ({
  getDbList: vi.fn(),
  scanDbKeys: vi.fn(),
  getCacheNames: vi.fn(),
  getCacheKeys: vi.fn(),
}));
vi.mock('#/api/infra/redis-cache', () => api);
vi.mock('#/api/error-feedback', () => ({
  takeErrorMessage: (error: Error) => error.message,
}));
const cleanups: Array<() => void> = [];
afterEach(() => {
  for (const cleanup of cleanups.splice(0)) cleanup();
  vi.resetAllMocks();
});

it('缓存加载按200条分页完整读取，失败会释放等待状态', async () => {
  api.getDbList.mockResolvedValue([
    { name: 'default', dbIndex: 0, label: 'default' },
  ]);
  api.scanDbKeys.mockResolvedValue(['test:key']);
  const groups = Array.from({ length: 201 }, (_, index) => ({
    cacheName: `group${index}`,
  }));
  const keys = Array.from({ length: 205 }, (_, index) => `group0:key${index}`);
  api.getCacheNames.mockImplementation(async ({ page, pageSize }) => {
    expect(pageSize).toBe(200);
    return {
      items: groups.slice((page - 1) * pageSize, page * pageSize),
      total: groups.length,
    };
  });
  api.getCacheKeys.mockImplementation(async ({ page, pageSize, keyPrefix }) => {
    expect(pageSize).toBe(200);
    expect(keyPrefix).toBe('group0');
    return {
      items: keys.slice((page - 1) * pageSize, page * pageSize),
      total: keys.length,
    };
  });
  let cache!: ReturnType<typeof useRedisCache>;
  const app = createApp({
    setup() {
      cache = useRedisCache();
      return () => h('div');
    },
  });
  const host = document.createElement('div');
  app.mount(host);
  cleanups.push(() => app.unmount());
  await vi.waitFor(() => expect(cache.cacheKeyRows.value).toHaveLength(205));
  expect(cache.cacheGroups.value).toHaveLength(201);
  expect(cache.rawKeys.value).toEqual(['test:key']);
  expect(api.getCacheNames).toHaveBeenCalledTimes(2);
  expect(api.getCacheKeys).toHaveBeenCalledTimes(2);
  expect(cache.loadingKeys.value).toBe(false);
  api.scanDbKeys.mockRejectedValueOnce(new Error('Redis连接失败'));
  await cache.loadKeys();
  expect(cache.loadingKeys.value).toBe(false);
  expect(cache.errorMessage.value).toBe('Redis连接失败');
});
