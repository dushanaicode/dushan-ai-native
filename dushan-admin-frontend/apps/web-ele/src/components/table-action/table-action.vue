<script setup lang="ts">
import type { ActionItem } from './types';

import { computed, onUnmounted, reactive, ref } from 'vue';

import { useAccess } from '@vben/access';
import { ChevronDown } from '@vben/icons';
import { $t } from '@vben/locales';

import { ElAlert, ElButton, ElDropdown, ElDropdownMenu } from 'element-plus';

import { takeErrorMessage } from '#/api/error-feedback';

import ActionTrigger from './action-trigger.vue';
import { canShowAction } from './types';

const props = withDefaults(
  defineProps<{
    actions?: ActionItem[];
    dropDownActions?: ActionItem[];
    divider?: boolean;
  }>(),
  { actions: () => [], dropDownActions: () => [], divider: false },
);
const emit = defineEmits<{ error: [error: unknown] }>();
const { hasAccessByCodes } = useAccess();
const permitted = (action: ActionItem) =>
  canShowAction(action, hasAccessByCodes);
const actions = computed(() => props.actions.filter(permitted));
const more = computed(() => props.dropDownActions.filter(permitted));
const pending = reactive(new Set<ActionItem>());
const failed = ref('');
const dropdown = ref<InstanceType<typeof ElDropdown>>();
let active = true;
onUnmounted(() => {
  active = false;
});
async function execute(action: ActionItem, fromDropdown = false) {
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
  failed.value = '';
  try {
    await (action.popConfirm
      ? action.popConfirm.confirm()
      : action.onClick?.());
    if (fromDropdown) dropdown.value?.handleClose();
  } catch (error) {
    if (active) {
      failed.value = takeErrorMessage(error, $t('utils.tableAction.failed'));
      emit('error', error);
    }
  } finally {
    pending.delete(action);
  }
}
</script>

<template>
  <div
    class="table-actions inline-flex items-center gap-2 align-middle whitespace-nowrap"
  >
    <ActionTrigger
      v-for="(action, index) in actions"
      :key="index"
      :action
      :pending="pending.has(action)"
      @execute="execute(action)"
    />
    <ElDropdown
      v-if="more.length"
      ref="dropdown"
      trigger="click"
      :hide-on-click="false"
    >
      <ElButton link type="primary">
        <span>{{ $t('utils.tableAction.more') }}</span>
        <ChevronDown class="ml-1 size-4" />
      </ElButton>
      <template #dropdown>
        <ElDropdownMenu>
          <ActionTrigger
            v-for="(action, index) in more"
            :key="index"
            :action
            dropdown
            :pending="pending.has(action)"
            :divided="index > 0 && (action.divider ?? divider)"
            @execute="execute(action, true)"
          />
        </ElDropdownMenu>
      </template>
    </ElDropdown>
    <ElAlert v-if="failed" type="error" :title="failed" @close="failed = ''" />
  </div>
</template>

<style scoped>
.table-actions :deep(.el-button.is-link) {
  height: 24px;
  padding: 0;
}
</style>
