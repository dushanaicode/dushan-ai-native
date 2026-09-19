<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemSmsLogApi } from '#/api/system/sms/log';

import { ref } from 'vue';

import { Page, useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  exportSmsLog,
  getExportSmsLogFields,
  getSmsLogPage,
} from '#/api/system/sms/log';
import { useExportModal } from '#/components';
import { $t } from '#/locales';

import { useGridColumns, useGridFormSchema } from './data';
import DetailModal from './modules/detail.vue';

defineOptions({ name: 'SystemSmsLog' });

const [DetailModalComponent, detailModalApi] = useVbenModal({
  connectedComponent: DetailModal,
  destroyOnClose: true,
});

const { ExportModal } = useExportModal();
const exportTableRef = ref();

function onDetail(row: SystemSmsLogApi.SmsLogRespVO) {
  detailModalApi.setData(row).open();
}

async function onExport() {
  const fields = await getExportSmsLogFields();
  const formValues = await gridApi.formApi.getValues();

  exportTableRef.value?.setData({
    columns: fields,
    exportApi: exportSmsLog,
    fileName: '短信日志数据.xls',
    searchParams: formValues,
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
          return await getSmsLogPage({
            ...formValues,
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
  } as VxeTableGridOptions<SystemSmsLogApi.SmsLogRespVO>,
});
</script>

<template>
  <Page auto-content-height>
    <DetailModalComponent />
    <ExportModal ref="exportTableRef" @success="handleExportSuccess" />

    <Grid table-title="短信日志">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.export'),
              type: 'primary',
              icon: ACTION_ICON.DOWNLOAD,
              auth: ['system:sms:log:export'],
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
              auth: ['system:sms:log:query'],
              onClick: onDetail.bind(null, row),
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
