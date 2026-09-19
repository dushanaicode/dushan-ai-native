<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraConfigDataApi } from '#/api/infra/config/data';

import { ref, watch } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { isEmpty } from '@vben/utils';

import { ElLoading, ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteConfigData,
  deleteConfigDataList,
  exportConfigData,
  getConfigDataPage,
  getExportConfigDataFields,
} from '#/api/infra/config/data';
import { useExportModal } from '#/components';
import { $t } from '#/locales';

import { useDataGridColumns, useDataGridFormSchema } from '../data';
import DataForm from './data-form.vue';

const props = withDefaults(
  defineProps<{
    typeId?: string;
  }>(),
  {
    typeId: undefined,
  },
);

const [DataFormModal, dataFormModalApi] = useVbenModal({
  connectedComponent: DataForm,
  destroyOnClose: true,
});

const { ExportModal } = useExportModal();
const exportTableRef = ref();
const checkedIds = ref<string[]>([]);

function normalizeSearchParams(
  values: Record<string, unknown>,
): InfraConfigDataApi.ConfigDataPageReqVO {
  return {
    createTime: Array.isArray(values.createTime)
      ? values.createTime
      : undefined,
    module: typeof values.module === 'string' ? values.module : undefined,
    name: typeof values.name === 'string' ? values.name : undefined,
    typeId: props.typeId,
  };
}

function handleRefresh() {
  checkedIds.value = [];
  gridApi.query();
}

function handleCreate() {
  if (!props.typeId) {
    ElMessage.warning('请先选择配置类型');
    return;
  }

  dataFormModalApi.setData({ lockTypeId: true, typeId: props.typeId }).open();
}

function handleEdit(row: InfraConfigDataApi.ConfigDataRespVO) {
  dataFormModalApi.setData(row).open();
}

async function handleExport() {
  const fields = await getExportConfigDataFields();
  const formValues = await gridApi.formApi.getValues();

  exportTableRef.value?.setData({
    columns: fields,
    exportApi: exportConfigData,
    fileName: '配置数据.xls',
    searchParams: normalizeSearchParams(formValues),
  });
  exportTableRef.value?.open();
}

function handleExportSuccess() {
  ElMessage.success($t('ui.actionMessage.operationSuccess'));
}

async function handleDelete(row: InfraConfigDataApi.ConfigDataRespVO) {
  const loading = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [row.name]),
  });

  try {
    await deleteConfigData(row.id);
    ElMessage.success($t('ui.actionMessage.deleteSuccess', [row.name]));
    handleRefresh();
  } finally {
    loading.close();
  }
}

async function handleDeleteBatch() {
  const loading = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [
      `${checkedIds.value.length}个配置数据`,
    ]),
  });

  try {
    await deleteConfigDataList(checkedIds.value);
    ElMessage.success($t('ui.actionMessage.deleteSuccess'));
    handleRefresh();
  } finally {
    loading.close();
  }
}

function handleRowCheckboxChange({
  records,
}: {
  records: InfraConfigDataApi.ConfigDataRespVO[];
}) {
  checkedIds.value = records.map((item) => item.id);
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useDataGridFormSchema(),
  },
  gridEvents: {
    checkboxAll: handleRowCheckboxChange,
    checkboxChange: handleRowCheckboxChange,
  },
  gridOptions: {
    columns: useDataGridColumns(),
    height: 'auto',
    keepSource: true,
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          return await getConfigDataPage({
            ...normalizeSearchParams(formValues),
            page: page.currentPage,
            pageSize: page.pageSize,
          });
        },
      },
    },
    rowConfig: {
      keyField: 'id',
    },
    toolbarConfig: {
      refresh: true,
      search: true,
    },
  } as VxeTableGridOptions<InfraConfigDataApi.ConfigDataRespVO>,
});

watch(
  () => props.typeId,
  () => {
    checkedIds.value = [];
    handleRefresh();
  },
);
</script>

<template>
  <div class="flex h-full flex-col">
    <DataFormModal @success="handleRefresh" />
    <ExportModal ref="exportTableRef" @success="handleExportSuccess" />

    <Grid table-title="配置数据">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.create', ['配置数据']),
              type: 'primary',
              icon: ACTION_ICON.ADD,
              disabled: !props.typeId,
              auth: ['infra:config:create'],
              onClick: handleCreate,
            },
            {
              label: $t('ui.actionTitle.export'),
              type: 'primary',
              icon: ACTION_ICON.DOWNLOAD,
              auth: ['infra:config:export'],
              onClick: handleExport,
            },
            {
              label: $t('ui.actionTitle.deleteBatch'),
              type: 'danger',
              icon: ACTION_ICON.DELETE,
              disabled: isEmpty(checkedIds),
              auth: ['infra:config:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [
                  `${checkedIds.length}个配置数据`,
                ]),
                confirm: handleDeleteBatch,
              },
            },
          ]"
        />
      </template>

      <template #actions="{ row }">
        <TableAction
          :actions="[
            {
              label: $t('common.edit'),
              type: 'text',
              icon: ACTION_ICON.EDIT,
              auth: ['infra:config:update'],
              onClick: handleEdit.bind(null, row),
            },
            {
              label: $t('common.delete'),
              type: 'text',
              danger: true,
              icon: ACTION_ICON.DELETE,
              auth: ['infra:config:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [row.name]),
                confirm: handleDelete.bind(null, row),
              },
            },
          ]"
        />
      </template>
    </Grid>
  </div>
</template>
