<script lang="ts" setup>
import type { WebSocketTestContext } from '../composables/use-websocket-test';

import { ElButton, ElCard, ElEmpty, ElTag } from 'element-plus';

const props = defineProps<{
  context: WebSocketTestContext;
}>();

const {
  clearReceivedLogs,
  formatLogTime,
  getLogTagType,
  getLogTypeText,
  receivedLogs,
} = props.context;
</script>

<template>
  <ElCard class="min-h-0" shadow="never">
    <template #header>
      <div class="flex items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <span class="i-ant-design:arrow-down-outlined text-success"></span>
          <span class="text-base font-medium">接收日志</span>
          <ElTag v-if="receivedLogs.length" type="success">
            {{ receivedLogs.length }} 条
          </ElTag>
        </div>
        <ElButton text type="primary" @click="clearReceivedLogs">
          清空
        </ElButton>
      </div>
    </template>

    <div class="h-full min-h-0 overflow-y-auto">
      <ElEmpty v-if="receivedLogs.length === 0" description="暂无接收日志" />
      <div v-else class="space-y-2">
        <div
          v-for="(log, index) in [...receivedLogs].reverse()"
          :key="`${log.time}-${index}`"
          class="rounded border border-border bg-background-deep p-3"
        >
          <div class="mb-2 flex items-center justify-between gap-3">
            <ElTag :type="getLogTagType(log.type)" size="small">
              {{ getLogTypeText(log.type) }}
            </ElTag>
            <span class="text-xs text-muted-foreground">
              {{ formatLogTime(log.time) }}
            </span>
          </div>
          <pre class="whitespace-pre-wrap break-words text-sm">{{
            log.message
          }}</pre>
        </div>
      </div>
    </div>
  </ElCard>
</template>
