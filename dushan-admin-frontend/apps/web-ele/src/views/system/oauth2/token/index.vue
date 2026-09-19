<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemOAuth2TokenApi } from '#/api/system/oauth2/token';

import { ref } from 'vue';

import { Page } from '@vben/common-ui';
import { isEmpty } from '@vben/utils';

import { ElLoading, ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteAccessToken,
  deleteAccessTokenList,
  getAccessTokenPage,
} from '#/api/system/oauth2/token';
import { $t } from '#/locales';

import { useGridColumns, useGridFormSchema } from './data';

defineOptions({ name: 'SystemOAuth2Token' });

const checkedIds = ref<string[]>([]);

function handleRefresh() {
  gridApi.query();
}

async function onDelete(row: SystemOAuth2TokenApi.OAuth2AccessTokenRespVO) {
  const loadingInstance = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [row.id]),
  });

  try {
    await deleteAccessToken(row.id);
    ElMessage.success($t('ui.actionMessage.deleteSuccess', [row.id]));
    handleRefresh();
  } finally {
    loadingInstance.close();
  }
}

async function onDeleteBatch() {
  const loadingInstance = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting'),
  });

  try {
    await deleteAccessTokenList(checkedIds.value);
    checkedIds.value = [];
    ElMessage.success($t('ui.actionMessage.deleteSuccess'));
    handleRefresh();
  } finally {
    loadingInstance.close();
  }
}

function handleRowCheckboxChange({
  records,
}: {
  records: SystemOAuth2TokenApi.OAuth2AccessTokenRespVO[];
}) {
  checkedIds.value = records.map((item) => item.id);
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useGridFormSchema(),
  },
  gridEvents: {
    checkboxAll: handleRowCheckboxChange,
    checkboxChange: handleRowCheckboxChange,
  },
  gridOptions: {
    columns: useGridColumns(),
    height: 'auto',
    keepSource: true,
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          return await getAccessTokenPage({
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
  } as VxeTableGridOptions<SystemOAuth2TokenApi.OAuth2AccessTokenRespVO>,
});
</script>

<template>
  <Page auto-content-height>
    <Grid table-title="OAuth2 访问令牌">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.deleteBatch'),
              type: 'danger',
              icon: ACTION_ICON.DELETE,
              disabled: isEmpty(checkedIds),
              auth: ['system:oauth2:token:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [
                  `${checkedIds.length}个 OAuth2 访问令牌`,
                ]),
                confirm: onDeleteBatch,
              },
            },
          ]"
        />
      </template>

      <template #actions="{ row }">
        <TableAction
          :actions="[
            {
              label: $t('common.delete'),
              type: 'text',
              danger: true,
              icon: ACTION_ICON.DELETE,
              auth: ['system:oauth2:token:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [row.id]),
                confirm: onDelete.bind(null, row),
              },
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
