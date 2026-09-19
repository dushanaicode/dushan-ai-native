<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemSmsChannelApi } from '#/api/system/sms/channel';

import { ref } from 'vue';

import { confirm, Page, useVbenModal } from '@vben/common-ui';
import { isEmpty } from '@vben/utils';

import { ElLoading, ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteSmsChannel,
  deleteSmsChannelList,
  getSmsChannelPage,
  updateSmsChannelStatus,
} from '#/api/system/sms/channel';
import { DICT_TYPE } from '#/constants/dict-types';
import { $t } from '#/locales';
import { useDictionary } from '#/services/dictionary/context';

import { useGridColumns, useGridFormSchema } from './data';
import SmsChannelForm from './modules/form.vue';

defineOptions({ name: 'SystemSmsChannel' });

const dictionary = useDictionary();

const [SmsChannelFormModal, smsChannelFormModalApi] = useVbenModal({
  connectedComponent: SmsChannelForm,
  destroyOnClose: true,
});

const checkedIds = ref<string[]>([]);

function handleRefresh() {
  gridApi.query();
}

function onCreate() {
  smsChannelFormModalApi.setData(null).open();
}

function onEdit(row: SystemSmsChannelApi.SmsChannelRespVO) {
  smsChannelFormModalApi.setData(row).open();
}

async function onDelete(row: SystemSmsChannelApi.SmsChannelRespVO) {
  const loadingInstance = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [row.signature]),
  });

  try {
    await deleteSmsChannel(row.id);
    ElMessage.success($t('ui.actionMessage.deleteSuccess', [row.signature]));
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
    await deleteSmsChannelList(checkedIds.value);
    checkedIds.value = [];
    ElMessage.success($t('ui.actionMessage.deleteSuccess'));
    handleRefresh();
  } finally {
    loadingInstance.close();
  }
}

async function handleStatusChange(
  newStatus: number,
  row: SystemSmsChannelApi.SmsChannelRespVO,
): Promise<boolean | undefined> {
  return new Promise((resolve, reject) => {
    const statusLabel = dictionary.getDictLabel(
      DICT_TYPE.COMMON_STATUS,
      newStatus,
    );
    confirm({
      content: `确认将【${row.signature}】的状态切换为【${statusLabel}】？`,
    })
      .then(async () => {
        await updateSmsChannelStatus(row.id, newStatus);
        ElMessage.success($t('ui.actionMessage.operationSuccess'));
        resolve(true);
      })
      .catch(() => reject(new Error('取消')));
  });
}

function handleRowCheckboxChange({
  records,
}: {
  records: SystemSmsChannelApi.SmsChannelRespVO[];
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
    columns: useGridColumns(handleStatusChange),
    height: 'auto',
    keepSource: true,
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          return await getSmsChannelPage({
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
  } as VxeTableGridOptions<SystemSmsChannelApi.SmsChannelRespVO>,
});
</script>

<template>
  <Page auto-content-height>
    <SmsChannelFormModal @success="handleRefresh" />

    <Grid table-title="短信渠道">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.create', ['短信渠道']),
              type: 'primary',
              icon: ACTION_ICON.ADD,
              auth: ['system:sms:channel:create'],
              onClick: onCreate,
            },
            {
              label: $t('ui.actionTitle.deleteBatch'),
              type: 'danger',
              icon: ACTION_ICON.DELETE,
              disabled: isEmpty(checkedIds),
              auth: ['system:sms:channel:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [
                  `${checkedIds.length}个短信渠道`,
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
              label: $t('common.edit'),
              type: 'text',
              icon: ACTION_ICON.EDIT,
              auth: ['system:sms:channel:update'],
              onClick: onEdit.bind(null, row),
            },
            {
              label: $t('common.delete'),
              type: 'text',
              danger: true,
              icon: ACTION_ICON.DELETE,
              auth: ['system:sms:channel:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [row.signature]),
                confirm: onDelete.bind(null, row),
              },
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
