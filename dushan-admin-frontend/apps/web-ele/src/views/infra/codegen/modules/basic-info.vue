<script lang="ts" setup>
import type { InfraCodegenApi } from '#/api/infra/codegen';

import { watch } from 'vue';

import { useVbenForm } from '#/adapter/form';

import { useBasicInfoFormSchema } from '../data';

defineOptions({ name: 'InfraCodegenBasicInfo' });

const props = defineProps<{
  table?: InfraCodegenApi.CodegenTableRespVO;
}>();

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    formItemClass: 'col-span-1',
    labelWidth: 100,
  },
  layout: 'horizontal',
  schema: useBasicInfoFormSchema(),
  showDefaultActions: false,
  wrapperClass: 'grid grid-cols-1 gap-4 md:grid-cols-2',
});

watch(
  () => props.table,
  async (table) => {
    await formApi.resetForm();
    if (table) {
      await formApi.setValues(table);
    }
  },
  { immediate: true },
);

defineExpose({
  async getData() {
    return (await formApi.getValues()) as Partial<InfraCodegenApi.CodegenTableRespVO>;
  },
  async validate() {
    const { valid } = await formApi.validate();
    return valid;
  },
});
</script>

<template>
  <Form />
</template>
