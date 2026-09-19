<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraMqApi } from '#/api/infra/mq';

import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page, useVbenModal } from '@vben/common-ui';

import { ElLoading, ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteMq,
  exportMq,
  getExportMqFields,
  getMqPage,
} from '#/api/infra/mq';
import { useExportModal } from '#/components';
import { $t } from '#/locales';

import { useGridColumns, useGridFormSchema } from './data';
import Detail from './modules/detail.vue';
import Form from './modules/form.vue';

defineOptions({ name: 'InfraMq' });

const router = useRouter();

const [FormModal, formModalApi] = useVbenModal({
  connectedComponent: Form,
  destroyOnClose: true,
});

const [DetailModal, detailModalApi] = useVbenModal({
  connectedComponent: Detail,
  destroyOnClose: true,
});

const { ExportModal } = useExportModal();
const exportTableRef = ref();
const checkedIds = ref<string[]>([]);

function normalizeSearchParams(
  values: Record<string, unknown>,
): InfraMqApi.MqPageReqVO {
  return {
    consumer: toOptionalString(values.consumer),
    createTime: toOptionalStringArray(values.createTime),
    topic: toOptionalString(values.topic),
  };
}

function toOptionalString(value: unknown) {
  return typeof value === 'string' && value ? value : undefined;
}

function toOptionalStringArray(value: unknown) {
  return Array.isArray(value) && value.every((item) => typeof item === 'string')
    ? value
    : undefined;
}

function handleRefresh() {
  checkedIds.value = [];
  gridApi.query();
}

function handleCreate() {
  formModalApi.setData(null).open();
}

function handleEdit(row: InfraMqApi.MqRespVO) {
  formModalApi.setData(row).open();
}

function handleDetail(row: InfraMqApi.MqRespVO) {
  detailModalApi.setData({ id: row.id }).open();
}

function handleViewLog(row?: InfraMqApi.MqRespVO) {
  router.push({
    name: 'InfraMqLog',
    query: row?.consumer ? { consumer: row.consumer } : {},
  });
}

async function handleExport() {
  const fields = await getExportMqFields();
  const formValues = await gridApi.formApi.getValues();

  exportTableRef.value?.setData({
    columns: fields,
    exportApi: exportMq,
    fileName: 'MQ消息定义.xls',
    searchParams: normalizeSearchParams(formValues),
  });
  exportTableRef.value?.open();
}

function handleExportSuccess() {
  ElMessage.success($t('ui.actionMessage.operationSuccess'));
}

async function handleDelete(row: InfraMqApi.MqRespVO) {
  const loading = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [row.topic]),
  });

  try {
    await deleteMq(row.id);
    ElMessage.success($t('ui.actionMessage.deleteSuccess', [row.topic]));
    handleRefresh();
  } finally {
    loading.close();
  }
}

async function handleDeleteBatch() {
  const loading = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [
      `${checkedIds.value.length} 个消息定义`,
    ]),
  });

  try {
    for (const id of checkedIds.value) {
      await deleteMq(id);
    }
    checkedIds.value = [];
    ElMessage.success($t('ui.actionMessage.deleteSuccess'));
    handleRefresh();
  } finally {
    loading.close();
  }
}

function handleRowCheckboxChange({
  records,
}: {
  records: InfraMqApi.MqRespVO[];
}) {
  checkedIds.value = records.map((item) => item.id);
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useGridFormSchema(),
  },
  gridOptions: {
    checkboxConfig: {
      highlight: true,
    },
    columns: useGridColumns(),
    height: 'auto',
    keepSource: true,
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          return await getMqPage({
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
  } as VxeTableGridOptions<InfraMqApi.MqRespVO>,
  gridEvents: {
    checkboxAll: handleRowCheckboxChange,
    checkboxChange: handleRowCheckboxChange,
  },
});
</script>

<template>
  <Page auto-content-height>
    <template #doc>
      <DocAlert title="消息队列" url="https://doc.iocoder.cn/message-queue/" />
    </template>

    <FormModal @success="handleRefresh" />
    <DetailModal />
    <ExportModal ref="exportTableRef" @success="handleExportSuccess" />

    <Grid table-title="MQ 消息定义列表">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.create', ['消息定义']),
              type: 'primary',
              icon: ACTION_ICON.ADD,
              auth: ['infra:mq:create'],
              onClick: handleCreate,
            },
            {
              label: $t('ui.actionTitle.export'),
              type: 'primary',
              icon: ACTION_ICON.DOWNLOAD,
              auth: ['infra:mq:export'],
              onClick: handleExport,
            },
            {
              label: '消费日志',
              type: 'primary',
              icon: ACTION_ICON.LOG,
              auth: ['infra:mq:log:query'],
              onClick: () => handleViewLog(),
            },
            {
              label: $t('ui.actionTitle.deleteBatch'),
              type: 'danger',
              icon: ACTION_ICON.DELETE,
              disabled: checkedIds.length === 0,
              auth: ['infra:mq:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [
                  `${checkedIds.length} 个消息定义`,
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
              auth: ['infra:mq:update'],
              onClick: handleEdit.bind(null, row),
            },
            {
              label: $t('common.delete'),
              type: 'text',
              danger: true,
              icon: ACTION_ICON.DELETE,
              auth: ['infra:mq:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [row.topic]),
                confirm: handleDelete.bind(null, row),
              },
            },
          ]"
          :drop-down-actions="[
            {
              label: $t('common.detail'),
              type: 'text',
              icon: ACTION_ICON.VIEW,
              auth: ['infra:mq:query'],
              onClick: handleDetail.bind(null, row),
            },
            {
              label: '消费日志',
              type: 'text',
              icon: ACTION_ICON.LOG,
              auth: ['infra:mq:log:query'],
              onClick: handleViewLog.bind(null, row),
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
