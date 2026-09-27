import type { Options, Rule } from '@form-create/element-ui';

import formCreate from '@form-create/element-ui';

/** 将序列化结果作为JS字符串字面量嵌入，保留引号、反斜杠和多行事件。 */
export function createVueForm(rules: Rule[], options: Options): string {
  const ruleJson = JSON.stringify(formCreate.toJson(rules)).replaceAll(
    '<',
    String.raw`\u003c`,
  );
  const optionJson = JSON.stringify(JSON.stringify(options)).replaceAll(
    '<',
    String.raw`\u003c`,
  );
  return `<script setup lang="ts">
import { getCurrentInstance, ref } from 'vue';
import formCreate from '@form-create/element-ui';
import { setupFormCreate } from '#/components/form-create/setup';

setupFormCreate(getCurrentInstance()!.appContext.app);
const FormCreate = formCreate.$form();
const rule = ref(formCreate.parseJson(${ruleJson}));
const option = ref(formCreate.parseJson(${optionJson}));
const values = ref({});
const emit = defineEmits<{ submit: [value: Record<string, unknown>] }>();
</script>

<template>
  <FormCreate v-model="values" :rule="rule" :option="option" @submit="emit('submit', $event)" />
</template>
`;
}
