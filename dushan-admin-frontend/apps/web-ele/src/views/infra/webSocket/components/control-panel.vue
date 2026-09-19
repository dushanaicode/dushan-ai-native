<script lang="ts" setup>
import type {
  WebSocketConnectionStatus,
  WebSocketTestContext,
} from '../composables/use-websocket-test';

import { computed } from 'vue';

import {
  ElButton,
  ElCard,
  ElDescriptions,
  ElDescriptionsItem,
  ElInput,
  ElOption,
  ElSelect,
  ElTag,
  ElTooltip,
} from 'element-plus';

const props = defineProps<{
  context: WebSocketTestContext;
}>();

const {
  applyPreset,
  broadcastMessage,
  canQuery,
  connectWebSocket,
  copyConnectionUrl,
  directMessage,
  disconnectWebSocket,
  isConnected,
  maskedConnectionUrl,
  presets,
  refreshStatus,
  selectedPreset,
  selectedUserId,
  sendBroadcast,
  sendDirectMessage,
  sending,
  sendToUser,
  statusInfo,
  statusLoading,
  targetUserMessage,
  targetUserType,
  userLoading,
  users,
  wsBaseUrl,
  wsLastError,
  wsStatus,
} = props.context;

const statusTextMap: Record<WebSocketConnectionStatus, string> = {
  backoff: '重连中',
  closed: '已断开',
  connecting: '连接中',
  disposed: '已销毁',
  exhausted: '异常',
  idle: '空闲',
  open: '已连接',
  recovering: '恢复中',
  ticket: '取票中',
};

const statusType = computed(() => {
  if (wsStatus.value === 'open') {
    return 'success';
  }
  if (
    ['backoff', 'connecting', 'recovering', 'ticket'].includes(wsStatus.value)
  ) {
    return 'warning';
  }
  if (wsStatus.value === 'exhausted') {
    return 'danger';
  }
  return 'info';
});
</script>

<template>
  <ElCard class="min-h-0" shadow="never">
    <template #header>
      <div class="flex items-center justify-between gap-3">
        <span class="text-base font-medium">控制中心</span>
        <ElTag :type="statusType">{{ statusTextMap[wsStatus] }}</ElTag>
      </div>
    </template>

    <div class="space-y-4 overflow-y-auto pr-1">
      <ElDescriptions :column="1" border size="small">
        <ElDescriptionsItem label="服务启用">
          <ElTag :type="statusInfo?.enabled ? 'success' : 'danger'">
            {{ statusInfo?.enabled ? '是' : '否' }}
          </ElTag>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="服务路径">
          {{ statusInfo?.path || '/infra/ws' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="发送器">
          {{ statusInfo?.senderType || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="登录校验">
          {{ statusInfo?.loginRequired ? '开启' : '关闭' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="连接数">
          {{ statusInfo?.activeConnections ?? 0 }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="wsLastError" label="最近错误">
          <ElTag type="danger">{{ wsLastError }}</ElTag>
        </ElDescriptionsItem>
      </ElDescriptions>

      <div class="space-y-2">
        <div class="text-sm font-medium">连接地址</div>
        <ElInput :model-value="wsBaseUrl" readonly />
        <div class="flex gap-2">
          <ElInput :model-value="maskedConnectionUrl" readonly />
          <ElTooltip content="复制完整连接地址" placement="top">
            <ElButton circle type="primary" @click="copyConnectionUrl">
              <span class="i-ant-design:copy-outlined"></span>
            </ElButton>
          </ElTooltip>
        </div>
        <div class="grid grid-cols-3 gap-2">
          <ElButton
            :disabled="isConnected"
            :loading="wsStatus === 'connecting'"
            type="primary"
            @click="connectWebSocket"
          >
            连接
          </ElButton>
          <ElButton
            :disabled="!isConnected"
            type="danger"
            @click="disconnectWebSocket"
          >
            断开
          </ElButton>
          <ElButton
            :disabled="!canQuery"
            :loading="statusLoading"
            @click="refreshStatus"
          >
            刷新
          </ElButton>
        </div>
      </div>

      <div class="space-y-2">
        <div class="text-sm font-medium">直连消息</div>
        <ElSelect
          v-model="selectedPreset"
          class="w-full"
          @change="(value) => applyPreset(value as string)"
        >
          <ElOption
            v-for="preset in presets"
            :key="preset.value"
            :label="preset.label"
            :value="preset.value"
          />
        </ElSelect>
        <ElInput v-model="directMessage" :rows="6" type="textarea" />
        <ElButton
          :disabled="!isConnected"
          class="w-full"
          type="primary"
          @click="sendDirectMessage"
        >
          发送直连消息
        </ElButton>
      </div>

      <div class="space-y-2">
        <div class="text-sm font-medium">HTTP 广播</div>
        <ElInput v-model="broadcastMessage" :rows="6" type="textarea" />
        <ElButton
          :disabled="!canQuery"
          :loading="sending"
          class="w-full"
          type="warning"
          @click="sendBroadcast"
        >
          广播到全部连接
        </ElButton>
      </div>

      <div class="space-y-2">
        <div class="text-sm font-medium">HTTP 定向发送</div>
        <div class="grid grid-cols-2 gap-2">
          <ElSelect v-model="targetUserType">
            <ElOption :value="2" label="管理员(2)" />
          </ElSelect>
          <ElSelect
            v-model="selectedUserId"
            :loading="userLoading"
            filterable
            placeholder="选择用户"
          >
            <ElOption
              v-for="user in users"
              :key="user.id"
              :label="user.nickname"
              :value="user.id"
            />
          </ElSelect>
        </div>
        <ElInput v-model="targetUserMessage" :rows="6" type="textarea" />
        <ElButton
          :disabled="!canQuery"
          :loading="sending"
          class="w-full"
          type="success"
          @click="sendToUser"
        >
          发送给用户
        </ElButton>
      </div>
    </div>
  </ElCard>
</template>
