<script lang="ts" setup>
import type { RedisKeyTagType, RedisValueView } from '../data';

import type { InfraRedisCacheApi } from '#/api/infra/redis-cache';

import { JsonViewer } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import {
  ElButton,
  ElCard,
  ElDescriptions,
  ElDescriptionsItem,
  ElEmpty,
  ElTag,
} from 'element-plus';

defineOptions({ name: 'InfraRedisCacheKeyDetailPanel' });

defineProps<{
  canDelete: boolean;
  dbLabel: string;
  detail: InfraRedisCacheApi.CacheKeyDetailRespVO | null;
  loading: boolean;
  ttlDisplay: string;
  typeTagType: RedisKeyTagType;
  valueView: RedisValueView;
}>();

const emit = defineEmits<{
  delete: [];
  refresh: [];
}>();
</script>

<template>
  <ElCard
    class="h-full overflow-hidden"
    :body-style="{ padding: 0, height: '100%' }"
  >
    <div v-loading="loading" class="flex h-full flex-col">
      <template v-if="detail">
        <div
          class="flex items-center justify-between gap-3 border-b border-border bg-muted/40 px-4 py-3"
        >
          <div class="flex min-w-0 flex-1 items-center gap-2">
            <ElTag :type="typeTagType" class="font-semibold uppercase">
              {{ detail.keyType }}
            </ElTag>
            <span
              class="truncate font-mono text-sm font-medium"
              :title="detail.key"
            >
              {{ detail.key }}
            </span>
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
              @click="emit('delete')"
            >
              <IconifyIcon icon="lucide:trash-2" class="mr-1 size-4" />
              删除
            </ElButton>
          </div>
        </div>

        <div class="border-b border-border px-4 py-3">
          <ElDescriptions :column="4" border size="small">
            <ElDescriptionsItem label="DB">
              {{ dbLabel || detail.dbName }}
            </ElDescriptionsItem>
            <ElDescriptionsItem label="类型">
              <ElTag :type="typeTagType" size="small">
                {{ detail.keyType }}
              </ElTag>
            </ElDescriptionsItem>
            <ElDescriptionsItem label="TTL">
              <span
                :class="{
                  'font-semibold text-destructive':
                    detail.ttl > 0 && detail.ttl < 60,
                }"
              >
                {{ ttlDisplay }}
              </span>
            </ElDescriptionsItem>
            <ElDescriptionsItem label="元素数">
              {{ detail.size ?? '-' }}
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
        <ElEmpty description="请在左侧选择一个 Key 查看详情" />
      </div>
    </div>
  </ElCard>
</template>
