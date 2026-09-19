<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemNoticeApi } from '#/api/system/notification/notice';

import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { confirm, Page, useVbenModal } from '@vben/common-ui';
import { isEmpty } from '@vben/utils';

import { ElLoading, ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteNotice,
  deleteNoticeList,
  getNoticePage,
  updateNoticeStatus,
} from '#/api/system/notification/notice';
import { DICT_TYPE } from '#/constants/dict-types';
import { $t } from '#/locales';
import { useDictionary } from '#/services/dictionary/context';

import { useGridColumns, useGridFormSchema } from './data';
import NoticeForm from './modules/form.vue';
import PushTarget from './modules/push-target.vue';

defineOptions({ name: 'SystemNotice' });

const dictionary = useDictionary();

const router = useRouter();
const checkedIds = ref<string[]>([]);

const [NoticeFormModal, noticeFormModalApi] = useVbenModal({
  connectedComponent: NoticeForm,
  destroyOnClose: true,
});

const [PushTargetModal, pushTargetModalApi] = useVbenModal({
  connectedComponent: PushTarget,
  destroyOnClose: true,
});

function handleRefresh() {
  gridApi.query();
}

function onCreate() {
  noticeFormModalApi.setData(null).open();
}

function onEdit(row: SystemNoticeApi.NoticeRespVO) {
  noticeFormModalApi.setData(row).open();
}

function onPush(row: SystemNoticeApi.NoticeRespVO) {
  pushTargetModalApi.setData(row).open();
}

function onViewLog(row?: SystemNoticeApi.NoticeRespVO) {
  router.push({
    path: '/system/notification/notice-log',
    query: row?.id ? { noticeId: row.id } : undefined,
  });
}

async function onDelete(row: SystemNoticeApi.NoticeRespVO) {
  const loadingInstance = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [row.title]),
  });

  try {
    await deleteNotice(row.id);
    ElMessage.success($t('ui.actionMessage.deleteSuccess', [row.title]));
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
    await deleteNoticeList(checkedIds.value);
    checkedIds.value = [];
    ElMessage.success($t('ui.actionMessage.deleteSuccess'));
    handleRefresh();
  } finally {
    loadingInstance.close();
  }
}

async function handleStatusChange(
  newStatus: number,
  row: SystemNoticeApi.NoticeRespVO,
): Promise<boolean | undefined> {
  return new Promise((resolve, reject) => {
    const statusLabel = dictionary.getDictLabel(
      DICT_TYPE.COMMON_STATUS,
      newStatus,
    );
    confirm({
      content: `确认将【${row.title}】的状态切换为【${statusLabel}】？`,
    })
      .then(async () => {
        await updateNoticeStatus(row.id, newStatus);
        ElMessage.success($t('ui.actionMessage.operationSuccess'));
        resolve(true);
      })
      .catch(() => reject(new Error('取消')));
  });
}

function handleRowCheckboxChange({
  records,
}: {
  records: SystemNoticeApi.NoticeRespVO[];
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
          return await getNoticePage({
            ...formValues,
            page: page.currentPage,
            pageSize: page.pageSize,
          });
        },
      },
    },
    rowConfig: {
      isHover: true,
      keyField: 'id',
    },
    toolbarConfig: {
      refresh: true,
      search: true,
    },
  } as VxeTableGridOptions<SystemNoticeApi.NoticeRespVO>,
});
</script>

<template>
  <Page auto-content-height>
    <NoticeFormModal @success="handleRefresh" />
    <PushTargetModal @success="handleRefresh" />

    <Grid table-title="通知管理">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.create', ['通知']),
              type: 'primary',
              icon: ACTION_ICON.ADD,
              auth: ['system:notification:create'],
              onClick: onCreate,
            },
            {
              label: '推送日志',
              type: 'primary',
              icon: 'lucide:list-checks',
              auth: ['system:notification:log:query'],
              onClick: () => onViewLog(),
            },
            {
              label: $t('ui.actionTitle.deleteBatch'),
              type: 'danger',
              icon: ACTION_ICON.DELETE,
              disabled: isEmpty(checkedIds),
              auth: ['system:notification:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [
                  `${checkedIds.length}个通知`,
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
              auth: ['system:notification:update'],
              disabled: row.builtin === 1,
              onClick: onEdit.bind(null, row),
            },
            {
              label: $t('common.delete'),
              type: 'text',
              danger: true,
              icon: ACTION_ICON.DELETE,
              auth: ['system:notification:delete'],
              disabled: row.builtin === 1,
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [row.title]),
                confirm: onDelete.bind(null, row),
              },
            },
          ]"
          :drop-down-actions="[
            {
              label: '推送',
              icon: 'lucide:send',
              auth: ['system:notification:send'],
              onClick: onPush.bind(null, row),
            },
            {
              label: '推送日志',
              icon: 'lucide:list-checks',
              auth: ['system:notification:log:query'],
              onClick: onViewLog.bind(null, row),
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
