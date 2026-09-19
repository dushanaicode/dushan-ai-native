<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemLoginLogApi } from '#/api/system/logger/loginlog';

import { ref } from 'vue';

import { Page, useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  exportLoginLog,
  getExportLoginLogFields,
  getLoginLogPage,
} from '#/api/system/logger/loginlog';
import { useExportModal } from '#/components';
import { $t } from '#/locales';

import { useGridColumns, useGridFormSchema } from './data';
import DetailModal from './modules/detail.vue';

defineOptions({ name: 'SystemLoginLog' });

const [DetailFormModal, detailFormModalApi] = useVbenModal({
  connectedComponent: DetailModal,
  destroyOnClose: true,
});

const { ExportModal } = useExportModal();
const exportTableRef = ref();

function onDetail(row: SystemLoginLogApi.LoginLogRespVO) {
  detailFormModalApi.setData(row).open();
}

async function onExport() {
  const fields = await getExportLoginLogFields();
  const formValues = await gridApi.formApi.getValues();

  exportTableRef.value?.setData({
    columns: fields,
    exportApi: exportLoginLog,
    fileName: '登录日志.xls',
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
          return await getLoginLogPage({
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
  } as VxeTableGridOptions<SystemLoginLogApi.LoginLogRespVO>,
});
</script>

<template>
  <Page auto-content-height>
    <DetailFormModal />
    <ExportModal ref="exportTableRef" @success="handleExportSuccess" />

    <Grid table-title="登录日志列表">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.export'),
              type: 'primary',
              icon: ACTION_ICON.DOWNLOAD,
              auth: ['system:logger:login-log:export'],
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
              auth: ['system:logger:login-log:query'],
              onClick: onDetail.bind(null, row),
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
