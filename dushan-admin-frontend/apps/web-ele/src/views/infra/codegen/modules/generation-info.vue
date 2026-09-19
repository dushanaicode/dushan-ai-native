<script lang="ts" setup>
import type { InfraCodegenApi } from '#/api/infra/codegen';

import { computed, ref, watch } from 'vue';

import { useVbenForm } from '#/adapter/form';
import { getCodegenTableList } from '#/api/infra/codegen';
import { InfraCodegenTemplateTypeEnum } from '#/constants/enums';

import {
  useGenerationInfoBaseFormSchema,
  useGenerationInfoSubTableFormSchema,
  useGenerationInfoTreeFormSchema,
} from '../data';

defineOptions({ name: 'InfraCodegenGenerationInfo' });

const props = defineProps<{
  columns?: InfraCodegenApi.CodegenColumnRespVO[];
  table?: InfraCodegenApi.CodegenTableRespVO;
}>();

const tables = ref<InfraCodegenApi.CodegenTableRespVO[]>([]);
const currentTemplateType = ref<number>(InfraCodegenTemplateTypeEnum.CRUD);

const isTreeTable = computed(
  () => currentTemplateType.value === InfraCodegenTemplateTypeEnum.TREE,
);
const isSubTable = computed(
  () => currentTemplateType.value === InfraCodegenTemplateTypeEnum.SUB,
);

const [BaseForm, baseFormApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    formItemClass: 'col-span-1',
    labelWidth: 100,
  },
  handleValuesChange(values, fieldsChanged) {
    if (fieldsChanged.includes('templateType')) {
      currentTemplateType.value = Number(values.templateType);
    }
  },
  layout: 'horizontal',
  schema: useGenerationInfoBaseFormSchema(),
  showDefaultActions: false,
  wrapperClass: 'grid grid-cols-1 gap-4 md:grid-cols-2',
});

const [TreeForm, treeFormApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    formItemClass: 'col-span-1',
    labelWidth: 100,
  },
  layout: 'horizontal',
  schema: [],
  showDefaultActions: false,
  wrapperClass: 'grid grid-cols-1 gap-4 md:grid-cols-2',
});

const [SubForm, subFormApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    formItemClass: 'col-span-1',
    labelWidth: 100,
  },
  layout: 'horizontal',
  schema: [],
  showDefaultActions: false,
  wrapperClass: 'grid grid-cols-1 gap-4 md:grid-cols-2',
});

async function updateExtraSchemas() {
  await treeFormApi.setState({
    schema: useGenerationInfoTreeFormSchema(props.columns || []),
  });
  await subFormApi.setState({
    schema: useGenerationInfoSubTableFormSchema(
      props.columns || [],
      tables.value,
      props.table?.id,
    ),
  });
}

async function loadGeneratedTables(table: InfraCodegenApi.CodegenTableRespVO) {
  tables.value = await getCodegenTableList({
    dataSourceConfigId: table.dataSourceConfigId,
  });
  await updateExtraSchemas();
}

watch(
  () => props.columns,
  () => {
    void updateExtraSchemas();
  },
  { immediate: true },
);

watch(
  () => props.table,
  async (table) => {
    await baseFormApi.resetForm();
    await treeFormApi.resetForm();
    await subFormApi.resetForm();

    if (!table) return;

    currentTemplateType.value = table.templateType;
    await baseFormApi.setValues(table);
    await updateExtraSchemas();
    await treeFormApi.setValues(table);
    await subFormApi.setValues(table);
    await loadGeneratedTables(table);
    await subFormApi.setValues(table);
  },
  { immediate: true },
);

async function getData(): Promise<Partial<InfraCodegenApi.CodegenTableRespVO>> {
  const baseValues = await baseFormApi.getValues();
  const treeValues = isTreeTable.value ? await treeFormApi.getValues() : {};
  const subValues = isSubTable.value ? await subFormApi.getValues() : {};

  return {
    ...baseValues,
    ...treeValues,
    ...subValues,
    masterTableId: isSubTable.value ? subValues.masterTableId : null,
    subJoinColumnId: isSubTable.value ? subValues.subJoinColumnId : null,
    subJoinMany: isSubTable.value ? subValues.subJoinMany : null,
    treeNameColumnId: isTreeTable.value ? treeValues.treeNameColumnId : null,
    treeParentColumnId: isTreeTable.value
      ? treeValues.treeParentColumnId
      : null,
  };
}

async function validate() {
  const { valid: baseValid } = await baseFormApi.validate();
  if (!baseValid) return false;

  if (isTreeTable.value) {
    const { valid } = await treeFormApi.validate();
    return valid;
  }

  if (isSubTable.value) {
    const { valid } = await subFormApi.validate();
    return valid;
  }

  return true;
}

defineExpose({
  getData,
  validate,
});
</script>

<template>
  <div class="space-y-4">
    <BaseForm />

    <div v-if="isTreeTable" class="codegen-extra-form">
      <div class="codegen-extra-form__title">树表信息</div>
      <TreeForm />
    </div>

    <div v-if="isSubTable" class="codegen-extra-form">
      <div class="codegen-extra-form__title">主子表信息</div>
      <SubForm />
    </div>
  </div>
</template>

<style scoped>
.codegen-extra-form {
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.codegen-extra-form__title {
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
</style>
