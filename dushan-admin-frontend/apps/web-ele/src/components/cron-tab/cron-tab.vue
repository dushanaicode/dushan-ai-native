<script setup lang="ts">
import type { CronField, CronMode } from './cron';

import { computed, ref, watch } from 'vue';

import { $t } from '@vben/locales';

import {
  ElAlert,
  ElButton,
  ElDialog,
  ElInput,
  ElInputNumber,
  ElOption,
  ElSelect,
} from 'element-plus';

import { cronFields, generateCron, newCronField, parseCron } from './cron';

const props = withDefaults(
  defineProps<{
    defaultValue?: string;
    disabled?: boolean;
    placeholder?: string;
    shortcuts?: { text: string; value: string }[];
  }>(),
  { defaultValue: '* * * * *', placeholder: undefined, shortcuts: () => [] },
);
const emit = defineEmits<{ change: [value: string] }>();
const model = defineModel<string>({ default: '' });
const visible = ref(false);
const failed = ref(false);
const fields = ref<CronField[]>(parseCron('* * * * *'));
const modes: CronMode[] = ['every', 'range', 'step', 'list'];
const shortcuts = computed(() => [
  { text: $t('utils.cron.eachMinute'), value: '* * * * *' },
  { text: $t('utils.cron.eachHour'), value: '0 * * * *' },
  { text: $t('utils.cron.eachDay'), value: '0 0 * * *' },
  { text: $t('utils.cron.eachMonth'), value: '0 0 1 * *' },
  { text: $t('utils.cron.eachWeek'), value: '0 0 * * 0' },
  ...props.shortcuts,
]);
const generated = computed(() => {
  try {
    return { value: generateCron(fields.value) };
  } catch {
    return { value: undefined };
  }
});
function options(index: number) {
  const field = cronFields[index] as (typeof cronFields)[number];
  return Array.from(
    { length: field.max - field.min + 1 },
    (_, offset) => offset + field.min,
  );
}
function setMode(mode: CronMode, index: number) {
  fields.value[index] = newCronField(mode, index);
}
function open() {
  if (props.disabled) return;
  failed.value = false;
  try {
    fields.value = parseCron(model.value || props.defaultValue);
    visible.value = true;
  } catch {
    failed.value = true;
  }
}
function apply(value: string) {
  if (props.disabled) return;
  model.value = value;
  emit('change', value);
  visible.value = false;
  failed.value = false;
}
watch([model, () => props.disabled], () => {
  visible.value = false;
});
</script>

<template>
  <div class="flex flex-col gap-2">
    <ElInput
      v-model="model"
      :disabled="disabled"
      :placeholder="placeholder"
      @change="(value) => emit('change', value)"
    >
      <template #append>
        <ElButton :disabled="disabled" @click="open">
          <span>{{ $t('utils.cron.generate') }}</span>
        </ElButton>
      </template>
    </ElInput>
    <ElSelect
      :disabled="disabled"
      :placeholder="$t('utils.cron.shortcut')"
      @change="apply"
    >
      <ElOption
        v-for="shortcut in shortcuts"
        :key="shortcut.value"
        :label="shortcut.text"
        :value="shortcut.value"
      />
    </ElSelect>
    <ElAlert
      v-if="failed"
      :title="$t('utils.cron.invalid')"
      type="error"
      :closable="false"
    />
    <ElDialog
      v-model="visible"
      :title="$t('utils.cron.generate')"
      width="min(700px, 95vw)"
      append-to-body
    >
      <div class="flex flex-col gap-3">
        <div
          v-for="(field, index) in fields"
          :key="index"
          class="flex flex-wrap items-center gap-2"
        >
          <span class="w-12">{{
            $t(`utils.cron.${cronFields[index]?.key}`)
          }}</span>
          <ElSelect
            :model-value="field.mode"
            class="!w-28"
            @change="(mode) => setMode(mode, index)"
          >
            <ElOption
              v-for="mode in modes"
              :key="mode"
              :label="$t(`utils.cron.${mode}`)"
              :value="mode"
            />
          </ElSelect>
          <template v-if="field.mode === 'range'">
            <ElInputNumber
              v-model="field.start"
              :min="cronFields[index]?.min"
              :max="cronFields[index]?.max"
            />
            <span>—</span>
            <ElInputNumber
              v-model="field.end"
              :min="cronFields[index]?.min"
              :max="cronFields[index]?.max"
            />
          </template>
          <template v-if="field.mode === 'step'">
            <ElSelect v-model="field.start" class="!w-24">
              <ElOption label="*" value="*" /><ElOption
                v-for="value in options(index)"
                :key="value"
                :label="String(value)"
                :value="value"
              />
            </ElSelect>
            <span>/</span><ElInputNumber v-model="field.step" :min="1" />
          </template>
          <ElSelect
            v-if="field.mode === 'list'"
            v-model="field.values"
            multiple
            class="flex-1"
          >
            <ElOption
              v-for="value in options(index)"
              :key="value"
              :label="String(value)"
              :value="value"
            />
          </ElSelect>
        </div>
        <code v-if="generated.value">{{ generated.value }}</code>
        <ElAlert
          v-else
          :title="$t('utils.cron.invalid')"
          type="error"
          :closable="false"
        />
      </div>
      <template #footer>
        <ElButton @click="visible = false">
          <span>{{ $t('utils.cron.cancel') }}</span>
        </ElButton>
        <ElButton
          type="primary"
          :disabled="disabled || !generated.value"
          @click="apply(generated.value as string)"
        >
          <span>{{ $t('utils.cron.apply') }}</span>
        </ElButton>
      </template>
    </ElDialog>
  </div>
</template>
