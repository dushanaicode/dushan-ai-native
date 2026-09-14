<script setup lang="ts">
import type { TagStyle } from '../services/dictionary/types';

import { computed, ref, watch } from 'vue';

import { $t } from '@vben/locales';

import {
  ElButton,
  ElColorPicker,
  ElDialog,
  ElRadioButton,
  ElRadioGroup,
} from 'element-plus';

import TagPreview from './tag-preview.vue';
import { tagColors } from './tag-style';

const props = withDefaults(
  defineProps<{
    clearable?: boolean;
    dialogTitle?: string;
    disabled?: boolean;
    placeholder?: string;
    predefineColors?: string[];
    previewText?: string;
  }>(),
  {
    clearable: true,
    disabled: false,
    dialogTitle: undefined,
    placeholder: undefined,
    predefineColors: undefined,
    previewText: undefined,
  },
);
const emit = defineEmits<{ change: [value: null | TagStyle] }>();
const model = defineModel<null | TagStyle>({ default: null });
const visible = ref(false);
const draft = ref<TagStyle>({ color: '', textColor: '', variant: 'solid' });
const colors = computed(
  () => props.predefineColors ?? Object.values(tagColors),
);
const variants = ['solid', 'outline', 'text', 'link'] as const;
watch(
  model,
  () => {
    visible.value = false;
  },
  { deep: true },
);

function open() {
  draft.value = model.value
    ? { ...model.value }
    : { color: '', textColor: '', variant: 'solid' };
  visible.value = true;
}

function apply() {
  model.value = { ...draft.value };
  emit('change', model.value);
  visible.value = false;
}

function clear() {
  model.value = null;
  emit('change', null);
  visible.value = false;
}
</script>

<template>
  <div class="inline-flex items-center gap-2">
    <ElButton :disabled @click="open">
      <TagPreview
        v-if="model"
        :tag-style="model"
        :text="previewText ?? $t('utils.tagEditor.preview')"
      />
      <span v-else>{{ placeholder ?? $t('utils.tagEditor.placeholder') }}</span>
    </ElButton>
    <ElButton v-if="clearable && model" :disabled link @click="clear">
      <span>{{ $t('utils.tagEditor.clear') }}</span>
    </ElButton>
    <ElDialog
      v-model="visible"
      :title="dialogTitle ?? $t('utils.tagEditor.title')"
      width="480px"
      append-to-body
    >
      <div class="flex flex-col gap-4">
        <ElRadioGroup v-model="draft.variant" :disabled>
          <ElRadioButton
            v-for="variant in variants"
            :key="variant"
            :value="variant"
          >
            <span>{{ $t(`utils.tagEditor.${variant}`) }}</span>
          </ElRadioButton>
        </ElRadioGroup>
        <label class="flex items-center gap-2">
          {{ $t('utils.tagEditor.color') }}
          <ElColorPicker
            :aria-label="$t('utils.tagEditor.color')"
            :model-value="draft.color"
            :predefine="colors"
            :disabled
            @update:model-value="(value) => (draft.color = value ?? '')"
          />
        </label>
        <label class="flex items-center gap-2">
          {{ $t('utils.tagEditor.textColor') }}
          <ElColorPicker
            :aria-label="$t('utils.tagEditor.textColor')"
            :model-value="draft.textColor"
            :predefine="colors"
            :disabled
            @update:model-value="(value) => (draft.textColor = value ?? '')"
          />
        </label>
        <TagPreview
          :tag-style="draft"
          :text="previewText ?? $t('utils.tagEditor.preview')"
        />
      </div>
      <template #footer>
        <ElButton @click="visible = false">
          <span>{{ $t('utils.tagEditor.cancel') }}</span>
        </ElButton>
        <ElButton type="primary" :disabled @click="apply">
          <span>{{ $t('utils.tagEditor.apply') }}</span>
        </ElButton>
      </template>
    </ElDialog>
  </div>
</template>
