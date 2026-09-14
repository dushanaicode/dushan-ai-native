<script setup lang="ts">
import type { PropType } from 'vue';

import type { DictionaryValue } from '../services/dictionary/types';
import type { TagVariant } from './tag-style';

import { computed, watch } from 'vue';

import { $t } from '@vben/locales';

import { ElButton } from 'element-plus';

import { useDictionary } from '../services/dictionary/context';
import { SessionChangedError } from '../services/session/coordinator';
import TagPreview from './tag-preview.vue';

const props = defineProps({
  type: { type: String, required: true },
  value: {
    // String 必须先于 Boolean，避免 Vue 将空字符串转换为 true。
    type: [String, Number, Boolean, Array] as PropType<
      DictionaryValue | DictionaryValue[] | null
    >,
    default: undefined,
  },
  variant: { type: String as PropType<TagVariant>, default: 'solid' },
});
const emit = defineEmits<{ error: [error: unknown] }>();
const dictionary = useDictionary();
const values = computed(() => {
  if (props.value === null || props.value === undefined) return [];
  const values = Array.isArray(props.value) ? props.value : [props.value];
  return values.filter((value) => value !== '');
});

async function ensure() {
  try {
    await dictionary.ensure();
  } catch (error) {
    if (
      error instanceof SessionChangedError ||
      (error instanceof DOMException && error.name === 'AbortError')
    )
      return;
    emit('error', error);
  }
}
watch([() => props.type, () => dictionary.version], ensure, {
  immediate: true,
});
</script>

<template>
  <span
    class="inline-flex flex-wrap gap-1"
    :aria-busy="dictionary.status === 'loading'"
  >
    <TagPreview
      v-for="(itemValue, index) in values"
      :key="index"
      :text="dictionary.getDictLabel(type, itemValue)"
      :tag-style="dictionary.getDictData(type, itemValue)?.tagStyle"
      :color-type="dictionary.getDictData(type, itemValue)?.colorType"
      :variant
    />
    <ElButton
      v-if="dictionary.status === 'error'"
      link
      type="danger"
      size="small"
      @click="ensure"
    >
      {{ $t('utils.dictionary.retry') }}
    </ElButton>
  </span>
</template>
