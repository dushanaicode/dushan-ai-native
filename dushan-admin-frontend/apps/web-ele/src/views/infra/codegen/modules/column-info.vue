<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraCodegenApi } from '#/api/infra/codegen';
import type { SystemDictTypeApi } from '#/api/system/dict/type';

import { nextTick, onMounted, ref, watch } from 'vue';

import { ElCheckbox, ElInput, ElOption, ElSelect } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getSimpleDictTypeList } from '#/api/system/dict/type';

import { useCodegenColumnTableColumns } from '../data';

defineOptions({ name: 'InfraCodegenColumnInfo' });

const props = defineProps<{
  columns?: InfraCodegenApi.CodegenColumnRespVO[];
}>();

const dictTypeOptions = ref<SystemDictTypeApi.DictTypeSimpleRespVO[]>([]);

const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: {
    border: true,
    columns: useCodegenColumnTableColumns(),
    data: [],
    height: 560,
    keepSource: true,
    pagerConfig: {
      enabled: false,
    },
    rowConfig: {
      keyField: 'id',
    },
    showOverflow: true,
    toolbarConfig: {
      enabled: false,
    },
  } as VxeTableGridOptions<InfraCodegenApi.CodegenColumnRespVO>,
});

watch(
  () => props.columns,
  async (columns) => {
    await nextTick();
    await gridApi.grid.loadData([...(columns || [])]);
  },
  { immediate: true },
);

onMounted(async () => {
  dictTypeOptions.value = await getSimpleDictTypeList();
});

defineExpose({
  getData() {
    return gridApi.grid.getData() as InfraCodegenApi.CodegenColumnRespVO[];
  },
});
</script>

<template>
  <Grid>
    <template #columnComment="{ row }">
      <ElInput v-model="row.columnComment" />
    </template>

    <template #fieldType="{ row, column }">
      <ElSelect v-model="row.fieldType" class="w-full">
        <ElOption
          v-for="option in column.params.options"
          :key="option.value"
          :label="option.label"
          :value="option.value"
        />
      </ElSelect>
    </template>

    <template #fieldName="{ row }">
      <ElInput v-model="row.fieldName" />
    </template>

    <template #createOperation="{ row }">
      <ElCheckbox v-model="row.createOperation" />
    </template>

    <template #updateOperation="{ row }">
      <ElCheckbox v-model="row.updateOperation" />
    </template>

    <template #listOperationResult="{ row }">
      <ElCheckbox v-model="row.listOperationResult" />
    </template>

    <template #listOperation="{ row }">
      <ElCheckbox v-model="row.listOperation" />
    </template>

    <template #listOperationCondition="{ row, column }">
      <ElSelect v-model="row.listOperationCondition" class="w-full">
        <ElOption
          v-for="option in column.params.options"
          :key="option.value"
          :label="option.label"
          :value="option.value"
        />
      </ElSelect>
    </template>

    <template #nullable="{ row }">
      <ElCheckbox v-model="row.nullable" />
    </template>

    <template #htmlType="{ row, column }">
      <ElSelect v-model="row.htmlType" class="w-full">
        <ElOption
          v-for="option in column.params.options"
          :key="option.value"
          :label="option.label"
          :value="option.value"
        />
      </ElSelect>
    </template>

    <template #dictType="{ row }">
      <ElSelect v-model="row.dictType" class="w-full" clearable filterable>
        <ElOption
          v-for="option in dictTypeOptions"
          :key="option.type"
          :label="`${option.name}（${option.type}）`"
          :value="option.type"
        />
      </ElSelect>
    </template>

    <template #example="{ row }">
      <ElInput v-model="row.example" />
    </template>
  </Grid>
</template>
