<script lang="ts" setup>
import type { RedisCacheKeyRow } from '../data';

import type { InfraRedisCacheApi } from '#/api/infra/redis-cache';

import { IconifyIcon } from '@vben/icons';

import {
  ElButton,
  ElCard,
  ElEmpty,
  ElTable,
  ElTableColumn,
} from 'element-plus';

defineOptions({ name: 'InfraRedisCacheGroupPanel' });

defineProps<{
  cacheGroups: InfraRedisCacheApi.CacheInfoRespVO[];
  cacheKeyRows: RedisCacheKeyRow[];
  canDelete: boolean;
  loadingCacheGroups: boolean;
  loadingCacheKeys: boolean;
  selectedCacheKey: string;
  selectedCacheName: string;
}>();

const emit = defineEmits<{
  (event: 'cacheKeyClick' | 'clearCacheKey', row: RedisCacheKeyRow): void;
  (
    event: 'cacheNameClick' | 'clearCacheName',
    row: InfraRedisCacheApi.CacheInfoRespVO,
  ): void;
  (event: 'refreshCacheGroups' | 'refreshCacheKeys'): void;
}>();

function handleCacheKeyClick(row: unknown) {
  emit('cacheKeyClick', row as RedisCacheKeyRow);
}

function handleCacheNameClick(row: unknown) {
  emit('cacheNameClick', row as InfraRedisCacheApi.CacheInfoRespVO);
}

function handleClearCacheKey(row: unknown) {
  emit('clearCacheKey', row as RedisCacheKeyRow);
}

function handleClearCacheName(row: unknown) {
  emit('clearCacheName', row as InfraRedisCacheApi.CacheInfoRespVO);
}
</script>

<template>
  <div class="grid h-full grid-cols-1 gap-4 xl:grid-cols-[420px_1fr]">
    <ElCard
      class="h-full overflow-hidden"
      :body-style="{
        padding: 0,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }"
    >
      <div
        class="flex items-center justify-between gap-3 border-b border-border bg-muted/40 px-4 py-3"
      >
        <div class="min-w-0">
          <div class="font-semibold">缓存分组</div>
          <div class="text-xs text-muted-foreground">
            已注册缓存前缀：{{ cacheGroups.length }}
          </div>
        </div>

        <ElButton
          :loading="loadingCacheGroups"
          size="small"
          @click="emit('refreshCacheGroups')"
        >
          <IconifyIcon icon="lucide:refresh-cw" class="mr-1 size-4" />
          刷新
        </ElButton>
      </div>

      <div class="min-h-0 flex-1 overflow-auto">
        <ElTable
          v-if="cacheGroups.length > 0"
          v-loading="loadingCacheGroups"
          :data="cacheGroups"
          height="100%"
          highlight-current-row
          row-key="cacheName"
          @row-click="handleCacheNameClick"
        >
          <ElTableColumn label="名称" min-width="160" prop="cacheName">
            <template #default="{ row }">
              <div class="min-w-0">
                <div
                  class="truncate font-mono text-sm"
                  :class="{
                    'font-semibold text-primary':
                      row.cacheName === selectedCacheName,
                  }"
                >
                  {{ row.cacheName }}
                </div>
                <div class="truncate text-xs text-muted-foreground">
                  {{ row.cacheValue || '-' }}
                </div>
              </div>
            </template>
          </ElTableColumn>

          <ElTableColumn
            v-if="canDelete"
            align="center"
            fixed="right"
            label="操作"
            width="86"
          >
            <template #default="{ row }">
              <ElButton
                link
                size="small"
                type="danger"
                @click.stop="handleClearCacheName(row)"
              >
                清理
              </ElButton>
            </template>
          </ElTableColumn>
        </ElTable>

        <div v-else class="flex h-full items-center justify-center">
          <ElEmpty description="暂无缓存分组" />
        </div>
      </div>
    </ElCard>

    <ElCard
      class="h-full overflow-hidden"
      :body-style="{
        padding: 0,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }"
    >
      <div
        class="flex items-center justify-between gap-3 border-b border-border bg-muted/40 px-4 py-3"
      >
        <div class="min-w-0">
          <div class="truncate font-semibold">
            Key 列表
            <span v-if="selectedCacheName" class="font-mono">
              / {{ selectedCacheName }}
            </span>
          </div>
          <div class="text-xs text-muted-foreground">
            当前数量：{{ cacheKeyRows.length }}
          </div>
        </div>

        <ElButton
          :disabled="!selectedCacheName"
          :loading="loadingCacheKeys"
          size="small"
          @click="emit('refreshCacheKeys')"
        >
          <IconifyIcon icon="lucide:refresh-cw" class="mr-1 size-4" />
          刷新
        </ElButton>
      </div>

      <div class="min-h-0 flex-1 overflow-auto">
        <ElTable
          v-if="cacheKeyRows.length > 0"
          v-loading="loadingCacheKeys"
          :data="cacheKeyRows"
          height="100%"
          highlight-current-row
          row-key="key"
          @row-click="handleCacheKeyClick"
        >
          <ElTableColumn label="缓存 Key" min-width="260" prop="key">
            <template #default="{ row }">
              <span
                class="block truncate font-mono text-sm"
                :class="{
                  'font-semibold text-primary': row.key === selectedCacheKey,
                }"
                :title="row.key"
              >
                {{ row.key }}
              </span>
            </template>
          </ElTableColumn>

          <ElTableColumn
            v-if="canDelete"
            align="center"
            fixed="right"
            label="操作"
            width="86"
          >
            <template #default="{ row }">
              <ElButton
                link
                size="small"
                type="danger"
                @click.stop="handleClearCacheKey(row)"
              >
                删除
              </ElButton>
            </template>
          </ElTableColumn>
        </ElTable>

        <div v-else class="flex h-full items-center justify-center">
          <ElEmpty
            :description="
              selectedCacheName ? '当前分组暂无 Key' : '请先选择缓存分组'
            "
          />
        </div>
      </div>
    </ElCard>
  </div>
</template>
