<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraCodegenApi } from '#/api/infra/codegen';

import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page, useVbenModal } from '@vben/common-ui';
import { downloadFileFromBlobPart, isEmpty } from '@vben/utils';

import { ElLoading, ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteCodegen,
  deleteCodegenList,
  downloadCodegen,
  getCodegenTablePage,
  syncCodegenFromDb,
} from '#/api/infra/codegen';
import { getDataSourceConfigList } from '#/api/infra/data-source-config';
import { $t } from '#/locales';

import { useGridColumns, useGridFormSchema } from './data';
import ImportTable from './modules/import-table.vue';
import PreviewCode from './modules/preview-code.vue';

defineOptions({ name: 'InfraCodegen' });

const router = useRouter();
const checkedIds = ref<string[]>([]);
const dataSourceConfigNameMap = ref(new Map<string, string>());

const [ImportTableModal, importTableModalApi] = useVbenModal({
  connectedComponent: ImportTable,
  destroyOnClose: true,
});

const [PreviewCodeModal, previewCodeModalApi] = useVbenModal({
  connectedComponent: PreviewCode,
  destroyOnClose: true,
});

function normalizeSearchParams(
  values: Record<string, unknown>,
): InfraCodegenApi.CodegenTablePageReqVO {
  return {
    createTime: Array.isArray(values.createTime)
      ? values.createTime.filter(
          (item): item is string => typeof item === 'string',
        )
      : undefined,
    tableComment: toOptionalString(values.tableComment),
    tableName: toOptionalString(values.tableName),
  };
}

function toOptionalString(value: unknown) {
  if (typeof value !== 'string') {
    return undefined;
  }
  const trimmedValue = value.trim();
  return trimmedValue || undefined;
}

async function loadDataSourceConfigNameMap() {
  const configs = await getDataSourceConfigList();
  dataSourceConfigNameMap.value = new Map(
    configs.map((item) => [item.id, item.name]),
  );
}

function getDataSourceConfigName(dataSourceConfigId: string) {
  return dataSourceConfigNameMap.value.get(dataSourceConfigId);
}

function sanitizeArchiveBaseName(value: string) {
  return value
    .trim()
    .replaceAll(/[^\w.-]+/g, '-')
    .replaceAll(/^-+|-+$/g, '');
}

function getCodegenArchiveFileName(row: InfraCodegenApi.CodegenTableRespVO) {
  const safeClassName = sanitizeArchiveBaseName(row.className);
  const safeBaseName = safeClassName || sanitizeArchiveBaseName(row.tableName);
  return `codegen-${safeBaseName}.zip`;
}

function handleRefresh() {
  checkedIds.value = [];
  gridApi.query();
}

function handleImport() {
  importTableModalApi.open();
}

function handleEdit(row: InfraCodegenApi.CodegenTableRespVO) {
  router.push({
    name: 'InfraCodegenEdit',
    query: { id: row.id },
  });
}

function handlePreview(row: InfraCodegenApi.CodegenTableRespVO) {
  previewCodeModalApi.setData(row).open();
}

async function handleDelete(row: InfraCodegenApi.CodegenTableRespVO) {
  const loading = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [row.tableName]),
  });

  try {
    await deleteCodegen(row.id);
    ElMessage.success($t('ui.actionMessage.deleteSuccess', [row.tableName]));
    handleRefresh();
  } finally {
    loading.close();
  }
}

async function handleDeleteBatch() {
  const loading = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [
      `${checkedIds.value.length}个生成表`,
    ]),
  });

  try {
    await deleteCodegenList(checkedIds.value);
    ElMessage.success($t('ui.actionMessage.deleteSuccess'));
    handleRefresh();
  } finally {
    loading.close();
  }
}

async function handleSync(row: InfraCodegenApi.CodegenTableRespVO) {
  const loading = ElLoading.service({
    fullscreen: true,
    text: `正在同步「${row.tableName}」表结构...`,
  });

  try {
    await syncCodegenFromDb(row.id);
    ElMessage.success($t('ui.actionMessage.operationSuccess'));
    handleRefresh();
  } finally {
    loading.close();
  }
}

async function handleDownload(row: InfraCodegenApi.CodegenTableRespVO) {
  const loading = ElLoading.service({
    fullscreen: true,
    text: `正在生成「${row.tableName}」代码...`,
  });

  try {
    const data = await downloadCodegen(row.id);
    downloadFileFromBlobPart({
      fileName: getCodegenArchiveFileName(row),
      source: data,
    });
    ElMessage.success($t('ui.actionMessage.operationSuccess'));
  } finally {
    loading.close();
  }
}

function handleRowCheckboxChange({
  records,
}: {
  records: InfraCodegenApi.CodegenTableRespVO[];
}) {
  checkedIds.value = records.map((item) => item.id);
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useGridFormSchema(),
  },
  gridEvents: {
    checkboxAll: handleRowCheckboxChange,
    checkboxChange: handleRowCheckboxChange,
  },
  gridOptions: {
    columns: useGridColumns(getDataSourceConfigName),
    height: 'auto',
    keepSource: true,
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          return await getCodegenTablePage({
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
  } as VxeTableGridOptions<InfraCodegenApi.CodegenTableRespVO>,
});

onMounted(() => {
  void loadDataSourceConfigNameMap();
});
</script>

<template>
  <Page auto-content-height>
    <ImportTableModal @success="handleRefresh" />
    <PreviewCodeModal />

    <Grid table-title="代码生成">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: '导入表',
              type: 'primary',
              icon: ACTION_ICON.ADD,
              auth: ['infra:codegen:create'],
              onClick: handleImport,
            },
            {
              label: $t('ui.actionTitle.deleteBatch'),
              type: 'danger',
              icon: ACTION_ICON.DELETE,
              disabled: isEmpty(checkedIds),
              auth: ['infra:codegen:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [
                  `${checkedIds.length}个生成表`,
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
              label: '预览',
              type: 'text',
              icon: ACTION_ICON.VIEW,
              auth: ['infra:codegen:preview'],
              onClick: handlePreview.bind(null, row),
            },
            {
              label: $t('common.edit'),
              type: 'text',
              icon: ACTION_ICON.EDIT,
              auth: ['infra:codegen:update'],
              onClick: handleEdit.bind(null, row),
            },
            {
              label: $t('common.delete'),
              type: 'text',
              danger: true,
              icon: ACTION_ICON.DELETE,
              auth: ['infra:codegen:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [row.tableName]),
                confirm: handleDelete.bind(null, row),
              },
            },
          ]"
          :drop-down-actions="[
            {
              label: '同步',
              type: 'text',
              icon: ACTION_ICON.REFRESH,
              auth: ['infra:codegen:update'],
              popConfirm: {
                title: `确认同步「${row.tableName}」的表结构？`,
                confirm: handleSync.bind(null, row),
              },
            },
            {
              label: '生成代码',
              type: 'text',
              icon: ACTION_ICON.DOWNLOAD,
              auth: ['infra:codegen:download'],
              onClick: handleDownload.bind(null, row),
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
