<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraDataSourceConfigApi } from '#/api/infra/data-source-config';

import { ref } from 'vue';

import { confirm, Page, useVbenModal } from '@vben/common-ui';

import { ElLoading, ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteDataSourceConfig,
  exportDataSourceConfig,
  getDataSourceConfigPage,
  getExportDataSourceConfigFields,
  testDataSourceConfig,
  updateDataSourceConfigStatus,
} from '#/api/infra/data-source-config';
import { useExportModal } from '#/components';
import { DICT_TYPE } from '#/constants/dict-types';
import { SwitchStatus } from '#/constants/status';
import { $t } from '#/locales';
import { useDictionary } from '#/services/dictionary/context';

import { useGridColumns, useGridFormSchema } from './data';
import Form from './modules/form.vue';

defineOptions({ name: 'InfraDataSourceConfig' });

const dictionary = useDictionary();

const [FormModal, formModalApi] = useVbenModal({
  connectedComponent: Form,
  destroyOnClose: true,
});

const { ExportModal } = useExportModal();
const exportTableRef = ref();

function normalizeSearchParams(
  values: Record<string, unknown>,
): InfraDataSourceConfigApi.DataSourceConfigPageReqVO {
  return {
    createTime: Array.isArray(values.createTime)
      ? values.createTime.filter(
          (item): item is string => typeof item === 'string',
        )
      : undefined,
    dbType: toOptionalString(values.dbType),
    name: toOptionalString(values.name),
    sourceType: toOptionalNumber(values.sourceType),
    status: toOptionalNumber(values.status),
  };
}

function toOptionalString(value: unknown) {
  if (typeof value !== 'string') {
    return undefined;
  }
  const trimmedValue = value.trim();
  return trimmedValue || undefined;
}

function toOptionalNumber(value: unknown) {
  if (value === undefined || value === null || value === '') {
    return undefined;
  }
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : undefined;
}

function handleRefresh() {
  gridApi.query();
}

function handleCreate() {
  formModalApi.setData(null).open();
}

function handleEdit(row: InfraDataSourceConfigApi.DataSourceConfigRespVO) {
  formModalApi.setData(row).open();
}

async function handleExport() {
  const fields = await getExportDataSourceConfigFields();
  const formValues = await gridApi.formApi.getValues();

  exportTableRef.value?.setData({
    columns: fields,
    exportApi: exportDataSourceConfig,
    fileName: '数据源配置.xls',
    searchParams: normalizeSearchParams(formValues),
  });
  exportTableRef.value?.open();
}

function handleExportSuccess() {
  ElMessage.success($t('ui.actionMessage.operationSuccess'));
}

async function handleDelete(
  row: InfraDataSourceConfigApi.DataSourceConfigRespVO,
) {
  if (row.isDefault) {
    ElMessage.warning('默认数据源不能删除');
    return;
  }

  const loading = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [row.name]),
  });

  try {
    await deleteDataSourceConfig(row.id);
    ElMessage.success($t('ui.actionMessage.deleteSuccess', [row.name]));
    handleRefresh();
  } finally {
    loading.close();
  }
}

async function handleTestConnection(
  row: InfraDataSourceConfigApi.DataSourceConfigRespVO,
) {
  const loading = ElLoading.service({
    fullscreen: true,
    text: `正在测试「${row.name}」连接...`,
  });

  try {
    const result = await testDataSourceConfig(row.id);
    if (result.success) {
      ElMessage.success(result.message || '数据源连接测试成功');
    } else {
      ElMessage.error(result.message || '数据源连接测试失败');
    }
  } finally {
    loading.close();
  }
}

async function handleStatusChange(
  newStatus: number,
  row: InfraDataSourceConfigApi.DataSourceConfigRespVO,
): Promise<boolean | undefined> {
  if (row.isDefault && newStatus === SwitchStatus.DISABLED) {
    ElMessage.warning('默认数据源不能禁用');
    return false;
  }

  return new Promise((resolve) => {
    const statusLabel = dictionary.getDictLabel(
      DICT_TYPE.COMMON_STATUS,
      newStatus,
    );
    confirm({
      content: `确认将「${row.name}」的状态切换为「${statusLabel}」？`,
    })
      .then(async () => {
        const loading = ElLoading.service({
          fullscreen: true,
          text: $t('ui.actionMessage.updating', [row.name]),
        });
        try {
          await updateDataSourceConfigStatus(row.id, newStatus);
          ElMessage.success($t('ui.actionMessage.operationSuccess'));
          resolve(true);
        } finally {
          loading.close();
        }
      })
      .catch(() => resolve(false));
  });
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useGridFormSchema(),
  },
  gridOptions: {
    columns: useGridColumns(handleStatusChange),
    height: 'auto',
    keepSource: true,
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          return await getDataSourceConfigPage({
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
  } as VxeTableGridOptions<InfraDataSourceConfigApi.DataSourceConfigRespVO>,
});
</script>

<template>
  <Page auto-content-height>
    <template #doc>
      <DocAlert
        title="数据源配置"
        url="https://doc.iocoder.cn/infra/data-source-config/"
      />
    </template>

    <FormModal @success="handleRefresh" />
    <ExportModal ref="exportTableRef" @success="handleExportSuccess" />

    <Grid table-title="数据源配置">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.create', ['数据源']),
              type: 'primary',
              icon: ACTION_ICON.ADD,
              auth: ['infra:data-source:create'],
              onClick: handleCreate,
            },
            {
              label: $t('ui.actionTitle.export'),
              type: 'primary',
              icon: ACTION_ICON.DOWNLOAD,
              auth: ['infra:data-source:export'],
              onClick: handleExport,
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
              auth: ['infra:data-source:update'],
              onClick: handleEdit.bind(null, row),
            },
            {
              label: $t('common.delete'),
              type: 'text',
              danger: true,
              icon: ACTION_ICON.DELETE,
              auth: ['infra:data-source:delete'],
              disabled: row.isDefault,
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [row.name]),
                confirm: handleDelete.bind(null, row),
              },
            },
          ]"
          :drop-down-actions="[
            {
              label: $t('common.test'),
              type: 'text',
              icon: 'lucide:test-tube-diagonal',
              auth: ['infra:data-source:query'],
              onClick: handleTestConnection.bind(null, row),
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
