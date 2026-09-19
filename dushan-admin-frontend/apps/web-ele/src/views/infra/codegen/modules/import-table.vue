<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraCodegenApi } from '#/api/infra/codegen';

import { nextTick, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { isEmpty } from '@vben/utils';

import { ElMessage } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { createCodegenList, getSchemaTableList } from '#/api/infra/codegen';
import { $t } from '#/locales';

import { useImportTableColumns, useImportTableFormSchema } from '../data';

defineOptions({ name: 'InfraCodegenImportTable' });

const emit = defineEmits<{
  success: [];
}>();

const selectedTableNames = ref<string[]>([]);

function toOptionalString(value: unknown) {
  if (typeof value !== 'string') {
    return undefined;
  }
  const trimmedValue = value.trim();
  return trimmedValue || undefined;
}

function handleSelectionChange({
  records,
}: {
  records: InfraCodegenApi.DatabaseTableRespVO[];
}) {
  selectedTableNames.value = records.map((item) => item.name);
}

function clearSelectedTables() {
  selectedTableNames.value = [];
  gridApi.grid.clearCheckboxRow();
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useImportTableFormSchema(),
    submitOnChange: true,
  },
  gridEvents: {
    checkboxAll: handleSelectionChange,
    checkboxChange: handleSelectionChange,
  },
  gridOptions: {
    columns: useImportTableColumns(),
    height: 420,
    keepSource: true,
    pagerConfig: {
      enabled: false,
    },
    proxyConfig: {
      ajax: {
        query: async (_params, formValues) => {
          clearSelectedTables();
          const dataSourceConfigId = toOptionalString(
            formValues.dataSourceConfigId,
          );

          if (!dataSourceConfigId) {
            return { list: [], total: 0 };
          }

          const list = await getSchemaTableList({
            dataSourceConfigId,
            tableComment: toOptionalString(formValues.tableComment),
            tableName: toOptionalString(formValues.tableName),
          });
          return { list, total: list.length };
        },
      },
    },
    rowConfig: {
      keyField: 'name',
    },
    toolbarConfig: {
      refresh: true,
      search: true,
    },
  } as VxeTableGridOptions<InfraCodegenApi.DatabaseTableRespVO>,
});

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    if (isEmpty(selectedTableNames.value)) {
      ElMessage.warning('请选择需要导入的表');
      return;
    }

    const values = await gridApi.formApi.getValues();
    const dataSourceConfigId = toOptionalString(values.dataSourceConfigId);
    if (!dataSourceConfigId) {
      ElMessage.warning('请选择数据源');
      return;
    }

    modalApi.lock();
    try {
      await createCodegenList({
        dataSourceConfigId,
        tableNames: selectedTableNames.value,
      });
      await modalApi.close();
      emit('success');
      ElMessage.success($t('ui.actionMessage.operationSuccess'));
    } finally {
      modalApi.unlock();
    }
  },
  async onOpenChange(isOpen: boolean) {
    if (!isOpen) {
      selectedTableNames.value = [];
      await gridApi.formApi.resetForm();
      return;
    }

    selectedTableNames.value = [];
    await nextTick();
    await gridApi.query();
  },
});
</script>

<template>
  <Modal class="w-3/5" title="导入数据库表">
    <Grid table-title="数据库表" />
  </Modal>
</template>
