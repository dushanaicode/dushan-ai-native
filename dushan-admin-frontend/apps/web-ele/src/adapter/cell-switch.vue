<script setup lang="ts">
import type { SwitchStatusValue } from '../constants/status';

import { onBeforeUnmount, ref } from 'vue';

import { $t } from '@vben/locales';

import { ElSwitch } from 'element-plus';

import { statusSwitchProps } from '../constants/status';

defineOptions({ inheritAttrs: false });

const props = defineProps<{
  change: (value: SwitchStatusValue) => Promise<unknown>;
  modelValue: SwitchStatusValue;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: SwitchStatusValue];
}>();

const loading = ref(false);
let active = true;
onBeforeUnmount(() => {
  active = false;
});

async function update(value: boolean | number | string) {
  if (loading.value) return;
  loading.value = true;
  try {
    const next = value as SwitchStatusValue;
    // 请求成功后才更新行数据，失败时仍显示原值。
    if ((await props.change(next)) !== false && active)
      emit('update:modelValue', next);
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <ElSwitch
    v-bind="{ ...$attrs, ...statusSwitchProps }"
    :active-text="$t('common.enabled')"
    :inactive-text="$t('common.disabled')"
    :loading="loading"
    :model-value="modelValue"
    inline-prompt
    @update:model-value="update"
  />
</template>
