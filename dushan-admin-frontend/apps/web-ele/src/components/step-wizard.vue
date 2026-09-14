<script setup lang="ts">
import type { Component } from 'vue';

import { ref, watch } from 'vue';

import { $t } from '@vben/locales';

import { ElButton, ElStep, ElSteps } from 'element-plus';

const props = withDefaults(
  defineProps<{
    steps: {
      title: string;
      description?: string;
      disabled?: boolean;
      icon?: Component | string;
    }[];
    current?: number;
    clickable?: boolean;
    loading?: boolean;
    mode?: 'default' | 'simple';
    showActions?: boolean;
    showStepInfo?: boolean;
    prevText?: string;
    nextText?: string;
    finishText?: string;
  }>(),
  {
    current: 0,
    clickable: true,
    mode: 'simple',
    showActions: true,
    showStepInfo: true,
    prevText: undefined,
    nextText: undefined,
    finishText: undefined,
  },
);
const emit = defineEmits<{
  'update:current': [value: number];
  change: [value: number];
  next: [from: number, to: number];
  prev: [from: number, to: number];
  complete: [];
}>();
const current = ref(props.current);
watch(
  () => props.current,
  (value) => {
    current.value = value;
  },
);
function setStep(index: number) {
  if (
    props.loading ||
    index < 0 ||
    index >= props.steps.length ||
    props.steps[index]?.disabled ||
    index === current.value
  )
    return;
  const from = current.value;
  current.value = index;
  emit('update:current', index);
  emit('change', index);
  if (index > from) emit('next', from, index);
  else emit('prev', from, index);
}
function nextStep() {
  setStep(current.value + 1);
}
function prevStep() {
  setStep(current.value - 1);
}
defineExpose({
  getCurrentStep: () => current.value,
  nextStep,
  prevStep,
  setStep,
});
</script>

<template>
  <div class="flex flex-col gap-4" :aria-busy="loading">
    <ElSteps :active="current" :simple="mode === 'simple'">
      <ElStep
        v-for="(step, index) in steps"
        :key="index"
        :title="step.title"
        :description="mode === 'default' ? step.description : undefined"
        :icon="step.icon"
        :class="{ 'cursor-pointer': clickable && !step.disabled }"
        @click="clickable && setStep(index)"
      />
    </ElSteps>
    <p v-if="showStepInfo && mode === 'simple'">
      {{ steps[current]?.description }}
    </p>
    <div v-for="(step, index) in steps" v-show="current === index" :key="index">
      <slot :name="`step-${index}`" :index :step></slot>
    </div>
    <div v-if="showActions" class="flex items-center justify-end gap-2">
      <slot name="extra-actions" :current></slot>
      <ElButton v-if="current > 0" :disabled="loading" @click="prevStep">
        <span>{{ prevText ?? $t('utils.wizard.prev') }}</span>
      </ElButton>
      <ElButton
        v-if="current < steps.length - 1"
        type="primary"
        :disabled="loading"
        @click="nextStep"
      >
        <span>{{ nextText ?? $t('utils.wizard.next') }}</span>
      </ElButton>
      <ElButton
        v-else
        type="primary"
        :disabled="loading"
        @click="emit('complete')"
      >
        <span>{{ finishText ?? $t('utils.wizard.finish') }}</span>
      </ElButton>
    </div>
  </div>
</template>
