<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue';

import { $t } from '@vben/locales';

import { ElSwitch } from 'element-plus';

import { notifyError } from '#/api/error-feedback';

import { statusSwitchProps } from '../constants/status';

defineOptions({ inheritAttrs: false });

const props = withDefaults(
  defineProps<{
    activeValue?: number;
    inactiveValue?: number;
    change: (value: number) => Promise<unknown>;
    modelValue: number;
  }>(),
  {
    activeValue: statusSwitchProps.activeValue,
    inactiveValue: statusSwitchProps.inactiveValue,
  },
);

const emit = defineEmits<{
  'update:modelValue': [value: number];
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
    const next = value ? props.activeValue : props.inactiveValue;
    // 请求成功后才更新行数据，失败时仍显示原值。
    if ((await props.change(next)) !== false && active)
      emit('update:modelValue', next);
  } catch (error) {
    if (active) notifyError(error);
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <ElSwitch
    v-bind="$attrs"
    :active-text="$t('common.enabled')"
    :inactive-text="$t('common.disabled')"
    :loading="loading"
    :model-value="modelValue === activeValue"
    inline-prompt
    @update:model-value="update"
  />
</template>
