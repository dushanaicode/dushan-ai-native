<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemOperateLogApi } from '#/api/system/logger/operatelog';

import { ref } from 'vue';

import { Page, useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  exportOperateLog,
  getExportOperateLogFields,
  getOperateLogPage,
} from '#/api/system/logger/operatelog';
import { useExportModal } from '#/components';
import { $t } from '#/locales';

import { useGridColumns, useGridFormSchema } from './data';
import DetailModal from './modules/detail.vue';

defineOptions({ name: 'SystemOperateLog' });

const [DetailFormModal, detailFormModalApi] = useVbenModal({
  connectedComponent: DetailModal,
  destroyOnClose: true,
});

const { ExportModal } = useExportModal();
const exportTableRef = ref();

function normalizeSearchParams(
  values: Record<string, any>,
): SystemOperateLogApi.OperateLogPageReqVO {
  return {
    ...values,
    bizId: typeof values.bizId === 'string' ? values.bizId : undefined,
    userId: typeof values.userId === 'string' ? values.userId : undefined,
  };
}

function onDetail(row: SystemOperateLogApi.OperateLogRespVO) {
  detailFormModalApi.setData(row).open();
}

async function onExport() {
  const fields = await getExportOperateLogFields();
  const formValues = await gridApi.formApi.getValues();

  exportTableRef.value?.setData({
    columns: fields,
    exportApi: exportOperateLog,
    fileName: '操作日志.xls',
    searchParams: normalizeSearchParams(formValues),
  });
  exportTableRef.value?.open();
}

function handleExportSuccess() {
  ElMessage.success($t('ui.actionMessage.operationSuccess'));
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
          return await getOperateLogPage({
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
  } as VxeTableGridOptions<SystemOperateLogApi.OperateLogRespVO>,
});
</script>

<template>
  <Page auto-content-height>
    <DetailFormModal />
    <ExportModal ref="exportTableRef" @success="handleExportSuccess" />

    <Grid table-title="操作日志列表">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.export'),
              type: 'primary',
              icon: ACTION_ICON.DOWNLOAD,
              auth: ['system:logger:operate-log:export'],
              onClick: onExport,
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
              auth: ['system:logger:operate-log:query'],
              onClick: onDetail.bind(null, row),
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
