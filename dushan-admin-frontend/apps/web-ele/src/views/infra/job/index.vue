<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraJobApi } from '#/api/infra/job';

import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { confirm, Page, useVbenModal } from '@vben/common-ui';
import { isEmpty } from '@vben/utils';

import { ElLoading, ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteJob,
  deleteJobList,
  exportJob,
  getExportJobFields,
  getJobPage,
  syncJob,
  triggerJob,
  updateJobStatus,
} from '#/api/infra/job';
import { useExportModal } from '#/components';
import { DICT_TYPE } from '#/constants/dict-types';
import { $t } from '#/locales';
import { useDictionary } from '#/services/dictionary/context';

import { useGridColumns, useGridFormSchema } from './data';
import Detail from './modules/detail.vue';
import Form from './modules/form.vue';

defineOptions({ name: 'InfraJob' });

const dictionary = useDictionary();

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

function toOptionalNumber(value: unknown) {
  if (value === undefined || value === null || value === '') {
    return undefined;
  }
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : undefined;
}

function normalizeSearchParams(
  values: Record<string, unknown>,
): InfraJobApi.JobPageReqVO {
  return {
    createTime: Array.isArray(values.createTime)
      ? values.createTime
      : undefined,
    handlerName:
      typeof values.handlerName === 'string' ? values.handlerName : undefined,
    name: typeof values.name === 'string' ? values.name : undefined,
    status: toOptionalNumber(values.status),
  };
}

function handleRefresh() {
  gridApi.query();
}

function handleCreate() {
  formModalApi.setData(null).open();
}

function handleEdit(row: InfraJobApi.JobRespVO) {
  formModalApi.setData(row).open();
}

function handleDetail(row: InfraJobApi.JobRespVO) {
  detailModalApi.setData({ id: row.id }).open();
}

function handleViewLog(row?: InfraJobApi.JobRespVO) {
  router.push({
    name: 'InfraJobLog',
    query: row?.id ? { jobId: row.id } : {},
  });
}

async function handleExport() {
  const fields = await getExportJobFields();
  const formValues = await gridApi.formApi.getValues();

  exportTableRef.value?.setData({
    columns: fields,
    exportApi: exportJob,
    fileName: '定时任务.xls',
    searchParams: normalizeSearchParams(formValues),
  });
  exportTableRef.value?.open();
}

function handleExportSuccess() {
  ElMessage.success($t('ui.actionMessage.operationSuccess'));
}

async function handleDelete(row: InfraJobApi.JobRespVO) {
  const loading = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [row.name]),
  });

  try {
    await deleteJob(row.id);
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
      `${checkedIds.value.length} 个任务`,
    ]),
  });

  try {
    await deleteJobList(checkedIds.value);
    checkedIds.value = [];
    ElMessage.success($t('ui.actionMessage.deleteSuccess'));
    handleRefresh();
  } finally {
    loading.close();
  }
}

async function handleTrigger(row: InfraJobApi.JobRespVO) {
  const loading = ElLoading.service({
    fullscreen: true,
    text: `正在执行「${row.name}」...`,
  });

  try {
    await triggerJob(row.id);
    ElMessage.success($t('ui.actionMessage.operationSuccess'));
  } finally {
    loading.close();
  }
}

async function handleSync() {
  const loading = ElLoading.service({
    fullscreen: true,
    text: '正在同步定时任务...',
  });

  try {
    await syncJob();
    ElMessage.success($t('ui.actionMessage.operationSuccess'));
    handleRefresh();
  } finally {
    loading.close();
  }
}

async function handleStatusChange(
  newStatus: number,
  row: InfraJobApi.JobRespVO,
): Promise<boolean | undefined> {
  return new Promise((resolve) => {
    const statusLabel = dictionary.getDictLabel(
      DICT_TYPE.INFRA_JOB_STATUS,
      newStatus,
    );
    confirm({
      content: `确认将「${row.name}」的任务状态切换为「${statusLabel}」？`,
    })
      .then(async () => {
        const loading = ElLoading.service({
          fullscreen: true,
          text: $t('ui.actionMessage.updating', [row.name]),
        });
        try {
          await updateJobStatus(row.id, newStatus);
          ElMessage.success($t('ui.actionMessage.operationSuccess'));
          resolve(true);
        } finally {
          loading.close();
        }
      })
      .catch(() => resolve(false));
  });
}

function handleRowCheckboxChange({
  records,
}: {
  records: InfraJobApi.JobRespVO[];
}) {
  checkedIds.value = records.map((item) => item.id);
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
          return await getJobPage({
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
  } as VxeTableGridOptions<InfraJobApi.JobRespVO>,
  gridEvents: {
    checkboxAll: handleRowCheckboxChange,
    checkboxChange: handleRowCheckboxChange,
  },
});
</script>

<template>
  <Page auto-content-height>
    <template #doc>
      <DocAlert title="定时任务" url="https://doc.iocoder.cn/job/" />
      <DocAlert title="异步任务" url="https://doc.iocoder.cn/async-task/" />
      <DocAlert title="消息队列" url="https://doc.iocoder.cn/message-queue/" />
    </template>

    <FormModal @success="handleRefresh" />
    <DetailModal />
    <ExportModal ref="exportTableRef" @success="handleExportSuccess" />

    <Grid table-title="定时任务列表">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.create', ['任务']),
              type: 'primary',
              icon: ACTION_ICON.ADD,
              auth: ['infra:job:create'],
              onClick: handleCreate,
            },
            {
              label: '同步任务',
              type: 'primary',
              icon: ACTION_ICON.REFRESH,
              auth: ['infra:job:create'],
              popConfirm: {
                title: '确认同步后端定时任务？',
                confirm: handleSync,
              },
            },
            {
              label: $t('ui.actionTitle.export'),
              type: 'primary',
              icon: ACTION_ICON.DOWNLOAD,
              auth: ['infra:job:export'],
              onClick: handleExport,
            },
            {
              label: '执行日志',
              type: 'primary',
              icon: ACTION_ICON.LOG,
              auth: ['infra:job:query'],
              onClick: () => handleViewLog(),
            },
            {
              label: $t('ui.actionTitle.deleteBatch'),
              type: 'danger',
              icon: ACTION_ICON.DELETE,
              disabled: isEmpty(checkedIds),
              auth: ['infra:job:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [
                  `${checkedIds.length} 个任务`,
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
              auth: ['infra:job:update'],
              onClick: handleEdit.bind(null, row),
            },
            {
              label: $t('common.delete'),
              type: 'text',
              danger: true,
              icon: ACTION_ICON.DELETE,
              auth: ['infra:job:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [row.name]),
                confirm: handleDelete.bind(null, row),
              },
            },
          ]"
          :drop-down-actions="[
            {
              label: $t('common.detail'),
              type: 'text',
              icon: ACTION_ICON.VIEW,
              auth: ['infra:job:query'],
              onClick: handleDetail.bind(null, row),
            },
            {
              label: '执行一次',
              type: 'text',
              icon: 'lucide:circle-play',
              auth: ['infra:job:trigger'],
              popConfirm: {
                title: `确认立即执行一次「${row.name}」？`,
                confirm: handleTrigger.bind(null, row),
              },
            },
            {
              label: '执行日志',
              type: 'text',
              icon: ACTION_ICON.LOG,
              auth: ['infra:job:query'],
              onClick: handleViewLog.bind(null, row),
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
