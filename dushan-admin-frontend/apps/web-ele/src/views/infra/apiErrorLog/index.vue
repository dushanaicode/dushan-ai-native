<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraApiErrorLogApi } from '#/api/infra/api-error-log';

import { ref } from 'vue';

import { Page, useVbenModal } from '@vben/common-ui';

import { ElLoading, ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  exportApiErrorLog,
  getApiErrorLogPage,
  getExportApiErrorLogFields,
  updateApiErrorLogStatus,
} from '#/api/infra/api-error-log';
import { useExportModal } from '#/components';
import { InfraApiErrorLogProcessStatusEnum } from '#/constants/enums';
import { $t } from '#/locales';

import { useGridColumns, useGridFormSchema } from './data';
import Detail from './modules/detail.vue';

defineOptions({ name: 'InfraApiErrorLog' });

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
): InfraApiErrorLogApi.ApiErrorLogPageReqVO {
  return {
    applicationName:
      typeof values.applicationName === 'string'
        ? values.applicationName
        : undefined,
    exceptionTime: Array.isArray(values.exceptionTime)
      ? values.exceptionTime
      : undefined,
    processStatus: toOptionalNumber(values.processStatus),
    requestUrl:
      typeof values.requestUrl === 'string' ? values.requestUrl : undefined,
    userId: typeof values.userId === 'string' ? values.userId : undefined,
    userType: toOptionalNumber(values.userType),
  };
}

function handleRefresh() {
  gridApi.query();
}

async function handleExport() {
  const fields = await getExportApiErrorLogFields();
  const formValues = await gridApi.formApi.getValues();

  exportTableRef.value?.setData({
    columns: fields,
    exportApi: exportApiErrorLog,
    fileName: 'API错误日志.xls',
    searchParams: normalizeSearchParams(formValues),
  });
  exportTableRef.value?.open();
}

function handleExportSuccess() {
  ElMessage.success($t('ui.actionMessage.operationSuccess'));
}

function handleDetail(row: InfraApiErrorLogApi.ApiErrorLogRespVO) {
  detailModalApi.setData(row).open();
}

async function handleProcess(
  row: InfraApiErrorLogApi.ApiErrorLogRespVO,
  processStatus: number,
) {
  if (row.processStatus !== InfraApiErrorLogProcessStatusEnum.INIT) {
    ElMessage.warning('该错误日志已处理，不能重复处理');
    return;
  }

  const loading = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.updating', [row.id]),
  });

  try {
    await updateApiErrorLogStatus(row.id, processStatus);
    ElMessage.success($t('ui.actionMessage.operationSuccess'));
    handleRefresh();
  } finally {
    loading.close();
  }
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
          return await getApiErrorLogPage({
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
  } as VxeTableGridOptions<InfraApiErrorLogApi.ApiErrorLogRespVO>,
});
</script>

<template>
  <Page auto-content-height>
    <template #doc>
      <DocAlert title="系统日志" url="https://doc.iocoder.cn/system-log/" />
    </template>

    <DetailModal />
    <ExportModal ref="exportTableRef" @success="handleExportSuccess" />

    <Grid table-title="API 错误日志">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.export'),
              type: 'primary',
              icon: ACTION_ICON.DOWNLOAD,
              auth: ['infra:logger:api-error-log:export'],
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
              auth: ['infra:logger:api-error-log:query'],
              onClick: handleDetail.bind(null, row),
            },
            {
              label: '已处理',
              type: 'text',
              auth: ['infra:logger:api-error-log:update-status'],
              ifShow:
                row.processStatus === InfraApiErrorLogProcessStatusEnum.INIT,
              popConfirm: {
                title: '确认标记为已处理？',
                confirm: handleProcess.bind(
                  null,
                  row,
                  InfraApiErrorLogProcessStatusEnum.DONE,
                ),
              },
            },
            {
              label: '已忽略',
              type: 'text',
              auth: ['infra:logger:api-error-log:update-status'],
              ifShow:
                row.processStatus === InfraApiErrorLogProcessStatusEnum.INIT,
              popConfirm: {
                title: '确认标记为已忽略？',
                confirm: handleProcess.bind(
                  null,
                  row,
                  InfraApiErrorLogProcessStatusEnum.IGNORE,
                ),
              },
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
