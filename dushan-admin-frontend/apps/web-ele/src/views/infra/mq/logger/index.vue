<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraMqLogApi } from '#/api/infra/mq/log';

import { ref, watch } from 'vue';
import { useRoute } from 'vue-router';

import { Page, useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  exportMqLog,
  getExportMqLogFields,
  getMqLogPage,
} from '#/api/infra/mq/log';
import { useExportModal } from '#/components';
import { $t } from '#/locales';

import { useGridColumns, useGridFormSchema } from './data';
import Detail from './modules/detail.vue';

defineOptions({ name: 'InfraMqLog' });

const route = useRoute();
const routeConsumer = parseRouteConsumer();

const [DetailModal, detailModalApi] = useVbenModal({
  connectedComponent: Detail,
  destroyOnClose: true,
});

const { ExportModal } = useExportModal();
const exportTableRef = ref();

function parseRouteConsumer() {
  const value = route.query.consumer;
  const rawValue = Array.isArray(value) ? value[0] : value;
  return typeof rawValue === 'string' && rawValue ? rawValue : undefined;
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
): InfraMqLogApi.MqLogPageReqVO {
  const [beginTime, endTime] = Array.isArray(values.beginEndTime)
    ? values.beginEndTime
    : [];

  return {
    beginTime: toOptionalString(beginTime),
    consumer: toOptionalString(values.consumer),
    endTime: toOptionalString(endTime),
    messageId: toOptionalString(values.messageId),
    status: toOptionalNumber(values.status),
  };
}

function toOptionalString(value: unknown) {
  return typeof value === 'string' && value ? value : undefined;
}

async function handleExport() {
  const fields = await getExportMqLogFields();
  const formValues = await gridApi.formApi.getValues();

  exportTableRef.value?.setData({
    columns: fields,
    exportApi: exportMqLog,
    fileName: 'MQ消费日志.xls',
    searchParams: normalizeSearchParams(formValues),
  });
  exportTableRef.value?.open();
}

function handleExportSuccess() {
  ElMessage.success($t('ui.actionMessage.operationSuccess'));
}

function handleDetail(row: InfraMqLogApi.MqLogRespVO) {
  detailModalApi.setData({ id: row.id }).open();
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useGridFormSchema(routeConsumer),
  },
  gridOptions: {
    columns: useGridColumns(),
    height: 'auto',
    keepSource: true,
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          return await getMqLogPage({
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
  } as VxeTableGridOptions<InfraMqLogApi.MqLogRespVO>,
});

watch(
  () => route.query,
  async () => {
    await gridApi.formApi.setValues({ consumer: parseRouteConsumer() });
    gridApi.query();
  },
);
</script>

<template>
  <Page auto-content-height>
    <template #doc>
      <DocAlert title="消息队列" url="https://doc.iocoder.cn/message-queue/" />
    </template>

    <DetailModal />
    <ExportModal ref="exportTableRef" @success="handleExportSuccess" />

    <Grid table-title="MQ 消费日志列表">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.export'),
              type: 'primary',
              icon: ACTION_ICON.DOWNLOAD,
              auth: ['infra:mq:log:export'],
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
              auth: ['infra:mq:log:query'],
              onClick: handleDetail.bind(null, row),
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
