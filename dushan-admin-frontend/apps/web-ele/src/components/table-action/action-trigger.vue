<script setup lang="ts">
import type { ActionItem } from './types';

import { computed, ref } from 'vue';

import { IconifyIcon, LoaderCircle } from '@vben/icons';

import { ElButton, ElDropdownItem, ElPopconfirm } from 'element-plus';

const props = defineProps<{
  action: ActionItem;
  pending: boolean;
  dropdown?: boolean;
  divided?: boolean;
}>();
const emit = defineEmits<{ execute: [] }>();
const confirming = ref(false);
const triggerProps = computed(() => {
  const { action, pending, dropdown } = props;
  const danger =
    action.danger || action.color === 'error' || action.type === 'danger';
  if (dropdown)
    return {
      class: [
        'flex w-full items-center py-1',
        danger ? 'text-destructive' : '',
      ],
    };
  return {
    disabled: action.disabled,
    loading: action.loading || pending,
    type: danger
      ? 'danger'
      : (action.color ??
        (action.type === 'text' ? 'primary' : action.type) ??
        'primary'),
    link: action.link || action.type === 'text',
    size: action.size,
    title: action.tooltip,
  };
});
function click() {
  if (props.action.disabled || props.action.loading || props.pending) return;
  if (props.action.popConfirm && !props.action.popConfirm.disabled)
    confirming.value = true;
  else emit('execute');
}
function confirm() {
  // 先清理可见状态，避免请求结束后 disabled 变化重新打开弹层。
  confirming.value = false;
  emit('execute');
}
function cancel() {
  confirming.value = false;
  props.action.popConfirm?.cancel?.();
}
</script>

<template>
  <component
    :is="dropdown ? ElDropdownItem : 'span'"
    v-bind="
      dropdown
        ? { disabled: action.disabled || action.loading || pending, divided }
        : { class: 'inline-flex' }
    "
    @click.stop="dropdown && click()"
  >
    <!-- 点击和菜单键盘统一由 click() 处理，避免默认触发器重复切换。 -->
    <ElPopconfirm
      v-model:visible="confirming"
      :trigger="[]"
      :trigger-keys="[]"
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
      @confirm="confirm"
      @cancel="cancel"
    >
      <template #reference>
        <component
          :is="dropdown ? 'span' : ElButton"
          v-bind="triggerProps"
          @click.stop="click"
        >
          <LoaderCircle
            v-if="dropdown && (pending || action.loading)"
            class="mr-2 size-4 animate-spin"
          />
          <IconifyIcon
            v-else-if="action.icon"
            :icon="action.icon"
            :class="dropdown ? 'mr-2 size-4' : 'mr-1 size-4'"
          />
          <span>{{ action.label }}</span>
        </component>
      </template>
    </ElPopconfirm>
  </component>
</template>
