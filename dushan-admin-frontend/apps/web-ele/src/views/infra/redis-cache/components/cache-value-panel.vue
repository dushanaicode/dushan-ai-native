<script lang="ts" setup>
import type { RedisValueView } from '../data';

import type { InfraRedisCacheApi } from '#/api/infra/redis-cache';

import { JsonViewer } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import {
  ElButton,
  ElCard,
  ElDescriptions,
  ElDescriptionsItem,
  ElEmpty,
} from 'element-plus';

defineOptions({ name: 'InfraRedisCacheValuePanel' });

defineProps<{
  cacheValue: InfraRedisCacheApi.CacheInfoRespVO | null;
  canDelete: boolean;
  loading: boolean;
  selectedCacheKey: string;
  selectedCacheName: string;
  selectedCacheRemark: string;
  valueView: RedisValueView;
}>();

const emit = defineEmits<{
  clearCacheKey: [];
  refresh: [];
}>();
</script>

<template>
  <ElCard
    class="h-full overflow-hidden"
    :body-style="{ padding: 0, height: '100%' }"
  >
    <div v-loading="loading" class="flex h-full flex-col">
      <template v-if="cacheValue">
        <div
          class="flex items-center justify-between gap-3 border-b border-border bg-muted/40 px-4 py-3"
        >
          <div class="min-w-0">
            <div class="truncate font-mono text-sm font-semibold">
              {{ cacheValue.cacheKey || selectedCacheKey }}
            </div>
            <div class="truncate text-xs text-muted-foreground">
              {{ selectedCacheName }} / {{ selectedCacheRemark }}
            </div>
          </div>

          <div class="flex flex-shrink-0 items-center gap-2">
            <ElButton size="small" @click="emit('refresh')">
              <IconifyIcon icon="lucide:refresh-cw" class="mr-1 size-4" />
              刷新
            </ElButton>
            <ElButton
              v-if="canDelete"
              size="small"
              type="danger"
              @click="emit('clearCacheKey')"
            >
              <IconifyIcon icon="lucide:trash-2" class="mr-1 size-4" />
              删除
            </ElButton>
          </div>
        </div>

        <div class="border-b border-border px-4 py-3">
          <ElDescriptions :column="2" border size="small">
            <ElDescriptionsItem label="缓存分组">
              {{ selectedCacheName }}
            </ElDescriptionsItem>
            <ElDescriptionsItem label="缓存 Key">
              <span class="font-mono">{{ cacheValue.cacheKey }}</span>
            </ElDescriptionsItem>
          </ElDescriptions>
        </div>

        <div class="flex min-h-0 flex-1 flex-col">
          <div class="border-b border-border bg-muted/40 px-4 py-2">
            <span class="text-sm font-semibold">Value</span>
          </div>

          <div class="min-h-0 flex-1 overflow-auto p-4">
            <JsonViewer
              v-if="valueView.isJson"
              :value="valueView.jsonValue"
              boxed
              copyable
              expanded
            />
            <pre
              v-else
              class="m-0 min-h-[240px] whitespace-pre-wrap break-all rounded border border-border bg-muted/40 p-3 font-mono text-sm leading-6"
              >{{ valueView.textValue || '(empty)' }}</pre>
          </div>
        </div>
      </template>

      <div v-else class="flex h-full items-center justify-center">
        <ElEmpty
          :description="
            selectedCacheKey ? '缓存值为空或不存在' : '请先选择缓存 Key 查看值'
          "
        />
      </div>
    </div>
  </ElCard>
</template>
