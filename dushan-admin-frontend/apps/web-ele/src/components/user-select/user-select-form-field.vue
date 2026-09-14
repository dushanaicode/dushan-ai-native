<script setup lang="ts">
import type { UserRecord, UserSelectProps, UserValue } from './selection';

import { computed, onUnmounted, ref, shallowRef, watch } from 'vue';

import { $t } from '@vben/locales';

import { ElAlert, ElButton, ElTag } from 'element-plus';

import { parseSelected, selectionValue, userIds } from './selection';
import UserSelectModal from './user-select-modal.vue';

const props = withDefaults(defineProps<UserSelectProps>(), {
  deptId: undefined,
  placeholder: undefined,
  showDeptFilter: true,
  size: 'default',
});
const emit = defineEmits<{
  change: [value: UserValue];
  error: [error: unknown];
}>();
const model = defineModel<UserValue>();
const visible = ref(false);
const failed = ref(false);
const cache = shallowRef(new Map<string, UserRecord>());
const ids = computed(() => userIds(model.value));
let controller = new AbortController();
watch(
  () => [ids.value, props.ports] as const,
  () => {
    visible.value = false;
    void load();
  },
  { immediate: true },
);
async function load() {
  controller.abort();
  controller = new AbortController();
  const signal = controller.signal;
  cache.value = new Map();
  failed.value = false;
  const requested = [...ids.value];
  if (requested.length === 0) return;
  try {
    const users = parseSelected(
      await props.ports.selected(requested, signal),
      requested,
    );
    signal.throwIfAborted();
    cache.value = new Map(users.map((user) => [user.id, user]));
  } catch (error) {
    if (!signal.aborted) {
      failed.value = true;
      emit('error', error);
    }
  }
}
function update(value: UserValue) {
  model.value = value;
  emit('change', value);
}
function remove(id: string) {
  if (!props.disabled)
    update(
      selectionValue(
        ids.value.filter((value) => value !== id),
        props.multiple,
      ),
    );
}
function open() {
  if (!props.disabled) visible.value = true;
}
onUnmounted(() => controller.abort());
</script>

<template>
  <div class="flex flex-col gap-2">
    <div
      class="flex min-h-8 cursor-pointer flex-wrap items-center gap-2 rounded border p-2"
      role="button"
      :tabindex="disabled ? -1 : 0"
      :aria-disabled="disabled"
      @click="open"
      @keydown.enter.prevent="open"
      @keydown.space.prevent="open"
    >
      <ElTag
        v-for="id in ids"
        :key="id"
        :closable="!disabled"
        @close.stop="remove(id)"
      >
        {{ cache.get(id)?.label ?? id }}
      </ElTag>
      <span v-if="ids.length === 0">{{
        placeholder ?? $t('utils.userSelect.placeholder')
      }}</span>
      <ElButton
        v-if="ids.length > 0"
        text
        :disabled="disabled"
        @click.stop="update(selectionValue([], multiple))"
      >
        <span>{{ $t('utils.userSelect.clear') }}</span>
      </ElButton>
    </div>
    <ElAlert
      v-if="failed"
      type="error"
      :title="$t('utils.userSelect.failed')"
      :closable="false"
    >
      <ElButton text @click="load">
        <span>{{ $t('utils.userSelect.retry') }}</span>
      </ElButton>
    </ElAlert>
    <UserSelectModal
      v-if="visible"
      v-model:visible="visible"
      :model-value="model"
      :ports="ports"
      :dept-id="deptId"
      :disabled="disabled"
      :multiple="multiple"
      :show-dept-filter="showDeptFilter"
      @confirm="update"
      @error="(error) => emit('error', error)"
    />
  </div>
</template>
