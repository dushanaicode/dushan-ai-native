<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraApiAccessLogApi } from '#/api/infra/api-access-log';

import { ref } from 'vue';

import { Page, useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  exportApiAccessLog,
  getApiAccessLogPage,
  getExportApiAccessLogFields,
} from '#/api/infra/api-access-log';
import { useExportModal } from '#/components';
import { $t } from '#/locales';

import { useGridColumns, useGridFormSchema } from './data';
import Detail from './modules/detail.vue';

defineOptions({ name: 'InfraApiAccessLog' });

const [DetailModal, detailModalApi] = useVbenModal({
  connectedComponent: Detail,
  destroyOnClose: true,
});

const { ExportModal } = useExportModal();
const exportTableRef = ref();

function toOptionalNumber(value: unknown) {
  if (value === undefined || value === null || value === '') {
    return undefined;
  }
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : undefined;
}

function normalizeSearchParams(
  values: Record<string, unknown>,
): InfraApiAccessLogApi.ApiAccessLogPageReqVO {
  return {
    applicationName:
      typeof values.applicationName === 'string'
        ? values.applicationName
        : undefined,
    beginTime: Array.isArray(values.beginTime) ? values.beginTime : undefined,
    duration: toOptionalNumber(values.duration),
    requestUrl:
      typeof values.requestUrl === 'string' ? values.requestUrl : undefined,
    resultCode: toOptionalNumber(values.resultCode),
    userId: typeof values.userId === 'string' ? values.userId : undefined,
    userType: toOptionalNumber(values.userType),
  };
}

async function handleExport() {
  const fields = await getExportApiAccessLogFields();
  const formValues = await gridApi.formApi.getValues();

  exportTableRef.value?.setData({
    columns: fields,
    exportApi: exportApiAccessLog,
    fileName: 'API访问日志.xls',
    searchParams: normalizeSearchParams(formValues),
  });
  exportTableRef.value?.open();
}

function handleExportSuccess() {
  ElMessage.success($t('ui.actionMessage.operationSuccess'));
}

function handleDetail(row: InfraApiAccessLogApi.ApiAccessLogRespVO) {
  detailModalApi.setData(row).open();
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useGridFormSchema(),
  },
  gridOptions: {
    columns: useGridColumns(),
    height: 'auto',
    keepSource: true,
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          return await getApiAccessLogPage({
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
  } as VxeTableGridOptions<InfraApiAccessLogApi.ApiAccessLogRespVO>,
});
</script>

<template>
  <Page auto-content-height>
    <template #doc>
      <DocAlert title="系统日志" url="https://doc.iocoder.cn/system-log/" />
    </template>

    <DetailModal />
    <ExportModal ref="exportTableRef" @success="handleExportSuccess" />

    <Grid table-title="API 访问日志">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.export'),
              type: 'primary',
              icon: ACTION_ICON.DOWNLOAD,
              auth: ['infra:logger:api-access-log:export'],
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
              auth: ['infra:logger:api-access-log:query'],
              onClick: handleDetail.bind(null, row),
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
