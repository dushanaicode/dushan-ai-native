<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraFileConfigApi } from '#/api/infra/file-config';

import { ref } from 'vue';

import { confirm, Page, useVbenModal } from '@vben/common-ui';
import { isEmpty, openWindow } from '@vben/utils';

import { ElLoading, ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteFileConfig,
  deleteFileConfigList,
  getFileConfigPage,
  testFileConfig,
  updateFileConfigMaster,
} from '#/api/infra/file-config';
import { $t } from '#/locales';

import { useGridColumns, useGridFormSchema } from './data';
import Form from './modules/form.vue';

defineOptions({ name: 'InfraFileConfig' });

const [FormModal, formModalApi] = useVbenModal({
  connectedComponent: Form,
  destroyOnClose: true,
});

const checkedIds = ref<string[]>([]);
const checkedRows = ref<InfraFileConfigApi.FileConfigRespVO[]>([]);

function toOptionalNumber(value: unknown) {
  if (value === undefined || value === null || value === '') {
    return undefined;
  }
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : undefined;
}

function toOptionalString(value: unknown) {
  if (typeof value !== 'string') {
    return undefined;
  }
  const trimmedValue = value.trim();
  return trimmedValue || undefined;
}

function normalizeSearchParams(
  values: Record<string, unknown>,
): InfraFileConfigApi.FileConfigPageReqVO {
  return {
    createTime: Array.isArray(values.createTime)
      ? values.createTime.filter(
          (item): item is string => typeof item === 'string',
        )
      : undefined,
    name: toOptionalString(values.name),
    status: toOptionalNumber(values.status),
    storage: toOptionalNumber(values.storage),
  };
}

function handleRefresh() {
  gridApi.query();
}

function handleCreate() {
  formModalApi.setData(null).open();
}

function handleEdit(row: InfraFileConfigApi.FileConfigRespVO) {
  formModalApi.setData(row).open();
}

async function handleMaster(row: InfraFileConfigApi.FileConfigRespVO) {
  if (row.master) {
    return;
  }

  const loading = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.updating', [row.name]),
  });

  try {
    await updateFileConfigMaster(row.id);
    ElMessage.success($t('ui.actionMessage.operationSuccess'));
    handleRefresh();
  } finally {
    loading.close();
  }
}

async function handleTest(row: InfraFileConfigApi.FileConfigRespVO) {
  const loading = ElLoading.service({
    fullscreen: true,
    text: '测试上传中...',
  });

  try {
    const url = await testFileConfig(row.id);
    await confirm({
      cancelText: '取消',
      confirmText: '访问',
      content: '测试上传成功，是否访问该文件？',
      title: '测试成功',
    });
    if (url) {
      openWindow(url);
    }
  } finally {
    loading.close();
  }
}

async function handleDelete(row: InfraFileConfigApi.FileConfigRespVO) {
  if (row.master) {
    ElMessage.warning('主配置不能删除');
    return;
  }

  const loading = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [row.name]),
  });

  try {
    await deleteFileConfig(row.id);
    ElMessage.success($t('ui.actionMessage.deleteSuccess', [row.name]));
    handleRefresh();
  } finally {
    loading.close();
  }
}

async function handleDeleteBatch() {
  if (checkedRows.value.some((item) => item.master)) {
    ElMessage.warning('主配置不能删除');
    return;
  }

  const loading = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [
      `${checkedIds.value.length}个文件配置`,
    ]),
  });

  try {
    await deleteFileConfigList(checkedIds.value);
    checkedIds.value = [];
    checkedRows.value = [];
    ElMessage.success($t('ui.actionMessage.deleteSuccess'));
    handleRefresh();
  } finally {
    loading.close();
  }
}

function handleSelectionChange({
  records,
}: {
  records: InfraFileConfigApi.FileConfigRespVO[];
}) {
  checkedRows.value = records;
  checkedIds.value = checkedRows.value.map((item) => item.id);
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useGridFormSchema(),
  },
  gridEvents: {
    checkboxAll: handleSelectionChange,
    checkboxChange: handleSelectionChange,
  },
  gridOptions: {
    columns: useGridColumns(),
    height: 'auto',
    keepSource: true,
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          return await getFileConfigPage({
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
  } as VxeTableGridOptions<InfraFileConfigApi.FileConfigRespVO>,
});
</script>

<template>
  <Page auto-content-height>
    <FormModal @success="handleRefresh" />

    <Grid table-title="文件配置列表">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.create', ['文件配置']),
              type: 'primary',
              icon: ACTION_ICON.ADD,
              auth: ['infra:file:config:create'],
              onClick: handleCreate,
            },
            {
              label: $t('ui.actionTitle.deleteBatch'),
              type: 'danger',
              icon: ACTION_ICON.DELETE,
              disabled: isEmpty(checkedIds),
              auth: ['infra:file:config:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [
                  `${checkedIds.length}个文件配置`,
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
              auth: ['infra:file:config:update'],
              onClick: handleEdit.bind(null, row),
            },
            {
              label: $t('common.delete'),
              type: 'text',
              danger: true,
              disabled: row.master,
              icon: ACTION_ICON.DELETE,
              auth: ['infra:file:config:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [row.name]),
                confirm: handleDelete.bind(null, row),
              },
            },
          ]"
          :drop-down-actions="[
            {
              label: '设为主配置',
              type: 'text',
              disabled: row.master,
              auth: ['infra:file:config:update'],
              popConfirm: {
                title: `是否要将「${row.name}」设为主配置？`,
                confirm: handleMaster.bind(null, row),
              },
            },
            {
              label: $t('common.test'),
              type: 'text',
              auth: ['infra:file:config:query'],
              onClick: handleTest.bind(null, row),
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
