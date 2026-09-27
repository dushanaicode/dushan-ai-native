<script setup lang="ts">
import { computed } from 'vue';

import { ElOption, ElSelect } from 'element-plus';

import { useDictionary } from '#/services/dictionary/context';

defineOptions({ name: 'NativeDictSelect' });
const props = withDefaults(
  defineProps<{
    dictType?: string;
    valueType?: 'number' | 'string';
    multiple?: boolean;
  }>(),
  {
    dictType: '',
    valueType: 'string',
    multiple: false,
  },
);
const model = defineModel<(number | string)[] | number | string>();
const dictionary = useDictionary();
const options = computed(() =>
  dictionary.getDictOptions(props.dictType, props.valueType),
);
</script>

<template>
  <ElSelect
    v-model="model"
    :multiple="multiple"
    clearable
    filterable
    class="w-full"
  >
    <ElOption
      v-for="option in options"
      :key="String(option.value)"
      :value="option.value"
      :label="option.label"
    />
  </ElSelect>
</template>
