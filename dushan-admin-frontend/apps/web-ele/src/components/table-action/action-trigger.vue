<script setup lang="ts">
import type { ActionItem } from './types';

import { IconifyIcon } from '@vben/icons';

import { ElButton, ElPopconfirm } from 'element-plus';

const props = defineProps<{ action: ActionItem; pending: boolean }>();
const emit = defineEmits<{ execute: [] }>();
function click() {
  if (!props.action.popConfirm || props.action.popConfirm.disabled)
    emit('execute');
}
</script>

<template>
  <ElPopconfirm
    :disabled="
      !action.popConfirm ||
      action.popConfirm.disabled ||
      action.disabled ||
      action.loading ||
      pending
    "
    :title="action.popConfirm?.title"
    :confirm-button-text="action.popConfirm?.okText"
    :cancel-button-text="action.popConfirm?.cancelText"
    @confirm="emit('execute')"
    @cancel="action.popConfirm?.cancel?.()"
  >
    <template #reference>
      <ElButton
        :type="
          action.danger || action.color === 'error'
            ? 'danger'
            : (action.color ?? action.type ?? 'primary')
        "
        :link="action.link || action.type === 'text'"
        :size="action.size"
        :disabled="action.disabled"
        :loading="action.loading || pending"
        :title="action.tooltip"
        @click.stop="click"
      >
        <IconifyIcon
          v-if="action.icon"
          :icon="action.icon"
          class="mr-1 size-4"
        />
        <span>{{ action.label }}</span>
      </ElButton>
    </template>
  </ElPopconfirm>
</template>
