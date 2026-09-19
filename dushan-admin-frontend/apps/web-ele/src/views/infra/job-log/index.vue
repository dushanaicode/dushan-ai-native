<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraJobLogApi } from '#/api/infra/job/log';

import { ref, watch } from 'vue';
import { useRoute } from 'vue-router';

import { Page, useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  exportJobLog,
  getExportJobLogFields,
  getJobLogPage,
} from '#/api/infra/job/log';
import { useExportModal } from '#/components';
import { $t } from '#/locales';

import { useGridColumns, useGridFormSchema } from './data';
import Detail from './modules/detail.vue';

defineOptions({ name: 'InfraJobLog' });

const route = useRoute();
const routeJobId = parseRouteJobId();

const [DetailModal, detailModalApi] = useVbenModal({
  connectedComponent: Detail,
  destroyOnClose: true,
});

const { ExportModal } = useExportModal();
const exportTableRef = ref();

function parseRouteJobId() {
  const value = route.query.jobId ?? route.query.id;
  const rawValue = Array.isArray(value) ? value[0] : value;
  const numericValue = Number(rawValue);
  return Number.isFinite(numericValue) && numericValue > 0
    ? numericValue
    : undefined;
}

function toOptionalNumber(value: unknown) {
  if (value === undefined || value === null || value === '') {
    return undefined;
  }
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : undefined;
}

function normalizeSearchParams(
  values: Record<string, unknown>,
): InfraJobLogApi.JobLogPageReqVO {
  const [beginTime, endTime] = Array.isArray(values.beginEndTime)
    ? values.beginEndTime
    : [];

  return {
    beginTime,
    endTime,
    handlerName:
      typeof values.handlerName === 'string' ? values.handlerName : undefined,
    jobId: typeof values.jobId === 'string' ? values.jobId : undefined,
    status: toOptionalNumber(values.status),
  };
}

async function handleExport() {
  const fields = await getExportJobLogFields();
  const formValues = await gridApi.formApi.getValues();

  exportTableRef.value?.setData({
    columns: fields,
    exportApi: exportJobLog,
    fileName: '定时任务日志.xls',
    searchParams: normalizeSearchParams(formValues),
  });
  exportTableRef.value?.open();
}

function handleExportSuccess() {
  ElMessage.success($t('ui.actionMessage.operationSuccess'));
}

function handleDetail(row: InfraJobLogApi.JobLogRespVO) {
  detailModalApi.setData({ id: row.id }).open();
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useGridFormSchema(routeJobId),
  },
  gridOptions: {
    columns: useGridColumns(),
    height: 'auto',
    keepSource: true,
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          return await getJobLogPage({
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
  } as VxeTableGridOptions<InfraJobLogApi.JobLogRespVO>,
});

watch(
  () => route.query,
  async () => {
    await gridApi.formApi.setValues({ jobId: parseRouteJobId() });
    gridApi.query();
  },
);
</script>

<template>
  <Page auto-content-height>
    <template #doc>
      <DocAlert title="定时任务" url="https://doc.iocoder.cn/job/" />
      <DocAlert title="异步任务" url="https://doc.iocoder.cn/async-task/" />
      <DocAlert title="消息队列" url="https://doc.iocoder.cn/message-queue/" />
    </template>

    <DetailModal />
    <ExportModal ref="exportTableRef" @success="handleExportSuccess" />

    <Grid table-title="任务日志列表">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.export'),
              type: 'primary',
              icon: ACTION_ICON.DOWNLOAD,
              auth: ['infra:job:export'],
              onClick: handleExport,
            },
          ]"
        />
      </template>

      <template #actions="{ row }">
        <TableAction
          :actions="[
            {
              label: $t('common.detail'),
              type: 'text',
              icon: ACTION_ICON.VIEW,
              auth: ['infra:job:query'],
              onClick: handleDetail.bind(null, row),
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
