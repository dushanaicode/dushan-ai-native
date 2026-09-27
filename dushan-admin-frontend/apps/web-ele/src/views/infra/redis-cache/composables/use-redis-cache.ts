import type { InfraRedisCacheApi } from '#/api/infra/redis-cache';
import type { PageParam, PageResult } from '#/api/types';

import { computed, onMounted, ref } from 'vue';

import { takeErrorMessage } from '#/api/error-feedback';
import {
  clearAllCaches,
  clearCacheByKey,
  clearCacheByName,
  deleteKey,
  getCacheKeys,
  getCacheNames,
  getCacheValue,
  getDbList,
  getKeyDetail,
  scanDbKeys,
} from '#/api/infra/redis-cache';

import {
  buildRedisKeyTree,
  DEFAULT_SCAN_PATTERN,
  formatTtl,
  getCacheGroupRemark,
  getKeyTypeTagType,
  normalizeRedisValue,
  REDIS_CACHE_PAGE_SIZE,
  toCacheKeyRows,
} from '../data';

async function loadCachePages<T>(
  fetchPage: (params: PageParam) => Promise<PageResult<T>>,
) {
  const items: T[] = [];
  let page = 1;
  let total: number;
  do {
    const result = await fetchPage({ page, pageSize: REDIS_CACHE_PAGE_SIZE });
    items.push(...result.items);
    total = result.total;
    page += 1;
  } while (items.length < total);
  return items;
}

export function useRedisCache() {
  const dbList = ref<InfraRedisCacheApi.CacheDbInfoRespVO[]>([]);
  const selectedDb = ref('');
  const searchPattern = ref(DEFAULT_SCAN_PATTERN);
  const rawKeys = ref<string[]>([]);
  const treeData = ref<ReturnType<typeof buildRedisKeyTree>>([]);
  const keyDetail = ref<InfraRedisCacheApi.CacheKeyDetailRespVO | null>(null);
  const loadingDb = ref(false);
  const loadingKeys = ref(false);
  const loadingDetail = ref(false);

  const cacheGroups = ref<InfraRedisCacheApi.CacheInfoRespVO[]>([]);
  const selectedCacheName = ref('');
  const cacheKeyRows = ref<ReturnType<typeof toCacheKeyRows>>([]);
  const selectedCacheKey = ref('');
  const cacheValue = ref<InfraRedisCacheApi.CacheInfoRespVO | null>(null);
  const loadingCacheGroups = ref(false);
  const loadingCacheKeys = ref(false);
  const loadingCacheValue = ref(false);

  const errorMessage = ref('');

  const currentDbLabel = computed(() => {
    return (
      dbList.value.find(
        (db: InfraRedisCacheApi.CacheDbInfoRespVO) =>
          db.name === selectedDb.value,
      )?.label ?? selectedDb.value
    );
  });

  const ttlDisplay = computed(() => formatTtl(keyDetail.value?.ttl));
  const typeTagType = computed(() =>
    getKeyTypeTagType(keyDetail.value?.keyType),
  );
  const keyValueView = computed(() =>
    normalizeRedisValue(keyDetail.value?.value),
  );

  const selectedCacheGroup = computed(() => {
    return (
      cacheGroups.value.find(
        (group) => group.cacheName === selectedCacheName.value,
      ) ?? null
    );
  });
  const selectedCacheRemark = computed(() =>
    getCacheGroupRemark(selectedCacheGroup.value),
  );
  const cacheValueView = computed(() =>
    normalizeRedisValue(cacheValue.value?.cacheValue),
  );

  function setError(error: unknown, message: string) {
    errorMessage.value = takeErrorMessage(error, message);
  }

  async function loadDbList() {
    loadingDb.value = true;
    errorMessage.value = '';
    try {
      const list = await getDbList();
      dbList.value = list;

      if (
        !list.some(
          (db: InfraRedisCacheApi.CacheDbInfoRespVO) =>
            db.name === selectedDb.value,
        )
      ) {
        selectedDb.value = list[0]?.name ?? '';
      }
    } catch (error) {
      setError(error, '获取 Redis DB 列表失败');
    } finally {
      loadingDb.value = false;
    }
  }

  async function loadKeys() {
    if (!selectedDb.value) {
      rawKeys.value = [];
      treeData.value = [];
      keyDetail.value = null;
      return;
    }

    loadingKeys.value = true;
    errorMessage.value = '';
    keyDetail.value = null;
    try {
      const pattern = searchPattern.value.trim() || DEFAULT_SCAN_PATTERN;
      const keys = await scanDbKeys(selectedDb.value, pattern);
      rawKeys.value = keys;
      treeData.value = buildRedisKeyTree(keys, selectedDb.value);
    } catch (error) {
      setError(error, '扫描 Redis key 失败');
    } finally {
      loadingKeys.value = false;
    }
  }

  async function handleDbChange() {
    keyDetail.value = null;
    await loadKeys();
  }

  async function loadKeyDetail(dbName: string, key: string) {
    loadingDetail.value = true;
    errorMessage.value = '';
    try {
      keyDetail.value = await getKeyDetail(dbName, key);
    } catch (error) {
      setError(error, '获取 Redis key 详情失败');
    } finally {
      loadingDetail.value = false;
    }
  }

  async function handleNodeClick(node: { dbName?: string; fullKey?: string }) {
    if (!node.dbName || !node.fullKey) {
      return;
    }
    await loadKeyDetail(node.dbName, node.fullKey);
  }

  async function refreshKeyDetail() {
    if (!keyDetail.value) {
      return;
    }
    await loadKeyDetail(keyDetail.value.dbName, keyDetail.value.key);
  }

  async function deleteCurrentDbKey() {
    if (!keyDetail.value) {
      return false;
    }

    const deleted = await deleteKey(
      keyDetail.value.dbName,
      keyDetail.value.key,
    );
    if (!deleted) {
      return false;
    }

    keyDetail.value = null;
    await loadKeys();
    return true;
  }

  async function loadCacheGroups() {
    loadingCacheGroups.value = true;
    errorMessage.value = '';
    try {
      cacheGroups.value = await loadCachePages(getCacheNames);

      if (
        !cacheGroups.value.some(
          (group) => group.cacheName === selectedCacheName.value,
        )
      ) {
        selectedCacheName.value = cacheGroups.value[0]?.cacheName ?? '';
      }
    } catch (error) {
      setError(error, '获取缓存分组失败');
    } finally {
      loadingCacheGroups.value = false;
    }
  }

  async function loadCacheKeys() {
    if (!selectedCacheName.value) {
      cacheKeyRows.value = [];
      selectedCacheKey.value = '';
      cacheValue.value = null;
      return;
    }

    loadingCacheKeys.value = true;
    errorMessage.value = '';
    cacheValue.value = null;
    selectedCacheKey.value = '';
    try {
      const keys = await loadCachePages((params) =>
        getCacheKeys({
          ...params,
          keyPrefix: selectedCacheName.value,
        }),
      );
      cacheKeyRows.value = toCacheKeyRows(keys);
    } catch (error) {
      setError(error, '获取缓存 key 列表失败');
    } finally {
      loadingCacheKeys.value = false;
    }
  }

  async function handleCacheNameClick(
    group: InfraRedisCacheApi.CacheInfoRespVO,
  ) {
    selectedCacheName.value = group.cacheName ?? '';
    await loadCacheKeys();
  }

  async function loadSelectedCacheValue() {
    if (!selectedCacheName.value || !selectedCacheKey.value) {
      cacheValue.value = null;
      return;
    }

    loadingCacheValue.value = true;
    errorMessage.value = '';
    try {
      cacheValue.value = await getCacheValue(
        selectedCacheName.value,
        selectedCacheKey.value,
      );
    } catch (error) {
      setError(error, '获取缓存值失败');
    } finally {
      loadingCacheValue.value = false;
    }
  }

  async function handleCacheKeyClick(row: { key: string }) {
    selectedCacheKey.value = row.key;
    await loadSelectedCacheValue();
  }

  async function refreshCacheValue() {
    await loadSelectedCacheValue();
  }

  async function clearSelectedCacheName() {
    if (!selectedCacheName.value) {
      return;
    }
    await clearCacheByName(selectedCacheName.value);
    await loadCacheKeys();
  }

  async function clearSelectedCacheKey() {
    if (!selectedCacheKey.value) {
      return;
    }
    await clearCacheByKey(selectedCacheKey.value);
    cacheValue.value = null;
    await loadCacheKeys();
  }

  async function clearAllRedisCaches() {
    await clearAllCaches();
    keyDetail.value = null;
    cacheValue.value = null;
    await Promise.all([loadKeys(), loadCacheKeys()]);
  }

  async function refreshAll() {
    await Promise.all([loadDbList(), loadCacheGroups()]);
    await Promise.all([loadKeys(), loadCacheKeys()]);
  }

  onMounted(() => {
    void refreshAll();
  });

  return {
    cacheGroups,
    cacheKeyRows,
    cacheValue,
    cacheValueView,
    clearAllRedisCaches,
    clearSelectedCacheKey,
    clearSelectedCacheName,
    currentDbLabel,
    dbList,
    deleteCurrentDbKey,
    errorMessage,
    handleCacheKeyClick,
    handleCacheNameClick,
    handleDbChange,
    handleNodeClick,
    keyDetail,
    keyValueView,
    loadCacheGroups,
    loadCacheKeys,
    loadKeys,
    loadingCacheGroups,
    loadingCacheKeys,
    loadingCacheValue,
    loadingDb,
    loadingDetail,
    loadingKeys,
    rawKeys,
    refreshAll,
    refreshCacheValue,
    refreshKeyDetail,
    searchPattern,
    selectedCacheKey,
    selectedCacheName,
    selectedCacheRemark,
    selectedDb,
    ttlDisplay,
    treeData,
    typeTagType,
  };
}
