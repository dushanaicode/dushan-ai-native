<script setup lang="ts">
import type { ActionItem } from './types';

import { computed, onUnmounted, reactive, ref } from 'vue';

import { useAccess } from '@vben/access';
import { $t } from '@vben/locales';

import {
  ElAlert,
  ElButton,
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
} from 'element-plus';

import ActionTrigger from './action-trigger.vue';
import { canShowAction } from './types';

const props = withDefaults(
  defineProps<{
    actions?: ActionItem[];
    dropDownActions?: ActionItem[];
    divider?: boolean;
  }>(),
  { actions: () => [], dropDownActions: () => [], divider: true },
);
const emit = defineEmits<{ error: [error: unknown] }>();
const { hasAccessByCodes } = useAccess();
const permitted = (action: ActionItem) =>
  canShowAction(action, hasAccessByCodes);
const actions = computed(() => props.actions.filter(permitted));
const more = computed(() => props.dropDownActions.filter(permitted));
const pending = reactive(new Set<ActionItem>());
const failed = ref(false);
let active = true;
onUnmounted(() => {
  active = false;
});
async function execute(action: ActionItem) {
  // 确认框打开期间可能已退出或降权，执行动作前重新核对。
  if (
    !active ||
    action.disabled ||
    action.loading ||
    pending.has(action) ||
    !permitted(action)
  )
    return;
  pending.add(action);
  failed.value = false;
  try {
    await (action.popConfirm
      ? action.popConfirm.confirm()
      : action.onClick?.());
  } catch (error) {
    if (active) {
      failed.value = true;
      emit('error', error);
    }
  } finally {
    pending.delete(action);
  }
}
</script>

<template>
  <div class="inline-flex items-center gap-2">
    <ActionTrigger
      v-for="(action, index) in actions"
      :key="index"
      :action
      :pending="pending.has(action)"
      @execute="execute(action)"
    />
    <ElDropdown v-if="more.length" trigger="click" :hide-on-click="false">
      <ElButton link type="primary">
        <span>{{ $t('utils.tableAction.more') }}</span>
      </ElButton>
      <template #dropdown>
        <ElDropdownMenu>
          <ElDropdownItem
            v-for="(action, index) in more"
            :key="index"
            :disabled="action.disabled || action.loading || pending.has(action)"
            :divided="index > 0 && (action.divider ?? divider)"
          >
            <ActionTrigger
              :action
              :pending="pending.has(action)"
              @execute="execute(action)"
            />
          </ElDropdownItem>
        </ElDropdownMenu>
      </template>
    </ElDropdown>
    <ElAlert
      v-if="failed"
      type="error"
      :title="$t('utils.tableAction.failed')"
      @close="failed = false"
    />
  </div>
</template>
