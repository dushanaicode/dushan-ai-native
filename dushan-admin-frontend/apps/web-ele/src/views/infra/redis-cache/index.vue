<script lang="ts" setup>
import type { RedisCacheKeyRow } from './data';

import { computed, ref } from 'vue';

import { useAccess } from '@vben/access';
import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import {
  ElAlert,
  ElButton,
  ElLoading,
  ElMessage,
  ElMessageBox,
  ElTabPane,
  ElTabs,
} from 'element-plus';

import CacheGroupPanel from './components/cache-group-panel.vue';
import CacheValuePanel from './components/cache-value-panel.vue';
import KeyDetailPanel from './components/key-detail-panel.vue';
import KeyTreePanel from './components/key-tree-panel.vue';
import { useRedisCache } from './composables/use-redis-cache';
import { CACHE_DELETE_PERMISSION } from './data';

defineOptions({ name: 'InfraRedisCache' });

const activeTab = ref('db');
const refreshing = ref(false);

const { hasAccessByCodes } = useAccess();
const canDelete = computed(() => hasAccessByCodes([CACHE_DELETE_PERMISSION]));

const {
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
} = useRedisCache();

async function handleRefreshAll() {
  refreshing.value = true;
  try {
    await refreshAll();
  } finally {
    refreshing.value = false;
  }
}

function isCancelAction(error: unknown) {
  return error === 'cancel' || error === 'close';
}

async function runDangerAction(
  loadingText: string,
  action: () => Promise<unknown>,
  successText: string,
) {
  const loading = ElLoading.service({
    fullscreen: true,
    text: loadingText,
  });

  try {
    const result = await action();
    if (result === false) {
      throw new Error('danger action returned false');
    }
    ElMessage.success(successText);
  } finally {
    loading.close();
  }
}

function ensureDeleteAccess() {
  if (canDelete.value) {
    return true;
  }
  ElMessage.warning('当前账号没有缓存删除权限');
  return false;
}

async function handleDeleteDbKey() {
  if (!ensureDeleteAccess()) {
    return;
  }

  const detail = keyDetail.value;
  if (!detail) {
    return;
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除 DB【${currentDbLabel.value}】中的 key【${detail.key}】吗？此操作不可恢复。`,
      '删除 Redis Key',
      {
        cancelButtonText: '取消',
        confirmButtonText: '删除',
        type: 'warning',
      },
    );
    await runDangerAction(
      `正在删除 ${detail.key}`,
      deleteCurrentDbKey,
      'Redis key 删除成功',
    );
  } catch (error) {
    if (!isCancelAction(error)) {
      ElMessage.error('Redis key 删除失败');
    }
  }
}

async function handleClearCacheName(cacheName?: null | string) {
  if (!ensureDeleteAccess()) {
    return;
  }

  if (!cacheName) {
    ElMessage.warning('请先选择缓存分组');
    return;
  }

  selectedCacheName.value = cacheName;

  try {
    await ElMessageBox.confirm(
      `确定要清理缓存分组【${cacheName}】下的所有 key 吗？此操作不可恢复。`,
      '清理缓存分组',
      {
        cancelButtonText: '取消',
        confirmButtonText: '清理',
        type: 'warning',
      },
    );
    await runDangerAction(
      `正在清理 ${cacheName}`,
      clearSelectedCacheName,
      '缓存分组清理成功',
    );
  } catch (error) {
    if (!isCancelAction(error)) {
      ElMessage.error('缓存分组清理失败');
    }
  }
}

async function handleClearCacheKey(row?: RedisCacheKeyRow) {
  if (!ensureDeleteAccess()) {
    return;
  }

  const cacheKey = row?.key ?? selectedCacheKey.value;
  if (!cacheKey) {
    ElMessage.warning('请先选择缓存 Key');
    return;
  }

  selectedCacheKey.value = cacheKey;

  try {
    await ElMessageBox.confirm(
      `确定要删除缓存 key【${cacheKey}】吗？此操作不可恢复。`,
      '删除缓存 Key',
      {
        cancelButtonText: '取消',
        confirmButtonText: '删除',
        type: 'warning',
      },
    );
    await runDangerAction(
      `正在删除 ${cacheKey}`,
      clearSelectedCacheKey,
      '缓存 key 删除成功',
    );
  } catch (error) {
    if (!isCancelAction(error)) {
      ElMessage.error('缓存 key 删除失败');
    }
  }
}

async function handleClearAll() {
  if (!ensureDeleteAccess()) {
    return;
  }

  try {
    await ElMessageBox.prompt(
      '该操作会对所有配置的 Redis client 执行 FLUSHDB。请输入 CLEAR 确认。',
      '清空全部 Redis 缓存',
      {
        cancelButtonText: '取消',
        confirmButtonText: '清空',
        inputErrorMessage: '请输入 CLEAR',
        inputPattern: /^CLEAR$/,
        type: 'warning',
      },
    );
    await runDangerAction(
      '正在清空全部 Redis 缓存',
      clearAllRedisCaches,
      '全部 Redis 缓存已清空',
    );
  } catch (error) {
    if (!isCancelAction(error)) {
      ElMessage.error('清空全部 Redis 缓存失败');
    }
  }
}
</script>

<template>
  <Page auto-content-height>
    <template #doc>
      <DocAlert title="Redis 缓存" url="https://doc.iocoder.cn/redis-cache/" />
      <DocAlert title="本地缓存" url="https://doc.iocoder.cn/local-cache/" />
    </template>

    <div class="space-y-4 p-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="min-w-0">
          <h2 class="text-lg font-semibold text-foreground">Redis 缓存</h2>
          <div class="text-sm text-muted-foreground">
            浏览 Redis DB、查看缓存值，并按权限执行清理操作
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <ElButton
            v-if="canDelete"
            :disabled="refreshing"
            type="danger"
            @click="handleClearAll"
          >
            <IconifyIcon icon="lucide:database-zap" class="mr-1 size-4" />
            清空全部
          </ElButton>
          <ElButton
            :loading="refreshing"
            type="primary"
            @click="handleRefreshAll"
          >
            <IconifyIcon icon="lucide:refresh-cw" class="mr-1 size-4" />
            刷新
          </ElButton>
        </div>
      </div>

      <ElAlert
        v-if="errorMessage"
        :closable="false"
        :title="errorMessage"
        show-icon
        type="error"
      />

      <ElTabs v-model="activeTab">
        <ElTabPane label="DB 浏览" name="db">
          <div
            class="grid h-[calc(100vh-260px)] min-h-[560px] grid-cols-1 gap-4 lg:grid-cols-[380px_1fr]"
          >
            <KeyTreePanel
              v-model:search-pattern="searchPattern"
              v-model:selected-db="selectedDb"
              :db-list="dbList"
              :loading-db="loadingDb"
              :loading-keys="loadingKeys"
              :raw-keys-count="rawKeys.length"
              :tree-data="treeData"
              @db-change="handleDbChange"
              @node-click="handleNodeClick"
              @refresh="handleRefreshAll"
              @search="loadKeys"
            />

            <KeyDetailPanel
              :can-delete="canDelete"
              :db-label="currentDbLabel"
              :detail="keyDetail"
              :loading="loadingDetail"
              :ttl-display="ttlDisplay"
              :type-tag-type="typeTagType"
              :value-view="keyValueView"
              @delete="handleDeleteDbKey"
              @refresh="refreshKeyDetail"
            />
          </div>
        </ElTabPane>

        <ElTabPane label="缓存分组" name="group">
          <div
            class="grid h-[calc(100vh-260px)] min-h-[560px] grid-cols-1 gap-4 2xl:grid-cols-[minmax(0,1fr)_520px]"
          >
            <CacheGroupPanel
              :cache-groups="cacheGroups"
              :cache-key-rows="cacheKeyRows"
              :can-delete="canDelete"
              :loading-cache-groups="loadingCacheGroups"
              :loading-cache-keys="loadingCacheKeys"
              :selected-cache-key="selectedCacheKey"
              :selected-cache-name="selectedCacheName"
              @cache-key-click="handleCacheKeyClick"
              @cache-name-click="handleCacheNameClick"
              @clear-cache-key="handleClearCacheKey"
              @clear-cache-name="
                (row) => handleClearCacheName(row.cacheName ?? '')
              "
              @refresh-cache-groups="loadCacheGroups"
              @refresh-cache-keys="loadCacheKeys"
            />

            <CacheValuePanel
              :cache-value="cacheValue"
              :can-delete="canDelete"
              :loading="loadingCacheValue"
              :selected-cache-key="selectedCacheKey"
              :selected-cache-name="selectedCacheName"
              :selected-cache-remark="selectedCacheRemark"
              :value-view="cacheValueView"
              @clear-cache-key="() => handleClearCacheKey()"
              @refresh="refreshCacheValue"
            />
          </div>
        </ElTabPane>
      </ElTabs>
    </div>
  </Page>
</template>
