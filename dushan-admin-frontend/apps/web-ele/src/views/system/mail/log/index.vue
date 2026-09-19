<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemMailLogApi } from '#/api/system/mail/log';

import { ref } from 'vue';

import { Page, useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  exportMailLog,
  getExportMailLogFields,
  getMailLogPage,
} from '#/api/system/mail/log';
import { useExportModal } from '#/components';
import { $t } from '#/locales';

import { useGridColumns, useGridFormSchema } from './data';
import DetailModal from './modules/detail.vue';

defineOptions({ name: 'SystemMailLog' });

const [DetailModalComponent, detailModalApi] = useVbenModal({
  connectedComponent: DetailModal,
  destroyOnClose: true,
});

const { ExportModal } = useExportModal();
const exportTableRef = ref();

function normalizeSearchParams(
  values: Record<string, any>,
): SystemMailLogApi.MailLogPageReqVO {
  const { sendTime, ...params } = values;
  if (Array.isArray(sendTime) && sendTime.length === 2) {
    params.sendTimeBegin = sendTime[0];
    params.sendTimeEnd = sendTime[1];
  }
  return params;
}

function onDetail(row: SystemMailLogApi.MailLogRespVO) {
  detailModalApi.setData(row).open();
}

async function onExport() {
  const fields = await getExportMailLogFields();
  const formValues = await gridApi.formApi.getValues();

  exportTableRef.value?.setData({
    columns: fields,
    exportApi: exportMailLog,
    fileName: '邮件日志数据.xls',
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
          return await getMailLogPage(
            normalizeSearchParams({
              ...formValues,
              page: page.currentPage,
              pageSize: page.pageSize,
            }),
          );
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
  } as VxeTableGridOptions<SystemMailLogApi.MailLogRespVO>,
});
</script>

<template>
  <Page auto-content-height>
    <DetailModalComponent />
    <ExportModal ref="exportTableRef" @success="handleExportSuccess" />

    <Grid table-title="邮件日志">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.export'),
              type: 'primary',
              icon: ACTION_ICON.DOWNLOAD,
              auth: ['system:mail:log:export'],
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
              auth: ['system:mail:log:query'],
              onClick: onDetail.bind(null, row),
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
