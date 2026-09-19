<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemNoticeMessageApi } from '#/api/system/notification/notice-message';

import { ref } from 'vue';

import { confirm, Page, useVbenModal } from '@vben/common-ui';
import { isEmpty } from '@vben/utils';

import { ElLoading, ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  getMyNoticeMessagePage,
  updateAllNoticeMessageRead,
  updateNoticeMessageRead,
} from '#/api/system/notification/notice-message';
import { $t } from '#/locales';

import { useGridColumns, useGridFormSchema } from './data';
import NoticeMessageDetail from './modules/detail.vue';

defineOptions({ name: 'SystemNoticeMessage' });

const checkedIds = ref<string[]>([]);

const [DetailModal, detailModalApi] = useVbenModal({
  connectedComponent: NoticeMessageDetail,
  destroyOnClose: true,
});

function handleRefresh() {
  gridApi.query();
}

function onDetail(row: SystemNoticeMessageApi.NoticeMessageRespVO) {
  detailModalApi.setData(row).open();
}

async function markRead(ids: string[]) {
  if (isEmpty(ids)) {
    return;
  }

  const loadingInstance = ElLoading.service({
    fullscreen: true,
    text: '正在标记已读',
  });

  try {
    await updateNoticeMessageRead(ids);
    checkedIds.value = [];
    ElMessage.success($t('ui.actionMessage.operationSuccess'));
    handleRefresh();
  } finally {
    loadingInstance.close();
  }
}

async function onRead(row: SystemNoticeMessageApi.NoticeMessageRespVO) {
  if (!row.readStatus) {
    await markRead([row.id]);
  }
  onDetail(row);
}

async function onReadBatch() {
  await markRead(checkedIds.value);
}

async function onReadAll() {
  confirm({
    content: '确认将所有站内信标记为已读？',
  })
    .then(async () => {
      const loadingInstance = ElLoading.service({
        fullscreen: true,
        text: '正在标记全部已读',
      });

      try {
        await updateAllNoticeMessageRead();
        checkedIds.value = [];
        ElMessage.success($t('ui.actionMessage.operationSuccess'));
        handleRefresh();
      } finally {
        loadingInstance.close();
      }
    })
    .catch(() => undefined);
}

function handleRowCheckboxChange({
  records,
}: {
  records: SystemNoticeMessageApi.NoticeMessageRespVO[];
}) {
  checkedIds.value = records
    .filter((item) => !item.readStatus)
    .map((item) => item.id);
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
    checkboxConfig: {
      checkMethod: ({ row }) => !row.readStatus,
    },
    columns: useGridColumns(),
    height: 'auto',
    keepSource: true,
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          return await getMyNoticeMessagePage({
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
  } as VxeTableGridOptions<SystemNoticeMessageApi.NoticeMessageRespVO>,
});
</script>

<template>
  <Page auto-content-height>
    <DetailModal />

    <Grid table-title="我的站内信">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: '标记已读',
              type: 'primary',
              icon: 'lucide:mail-check',
              disabled: isEmpty(checkedIds),
              onClick: onReadBatch,
            },
            {
              label: '全部已读',
              type: 'primary',
              icon: 'lucide:mail-open',
              onClick: onReadAll,
            },
          ]"
        />
      </template>

      <template #actions="{ row }">
        <TableAction
          :actions="[
            {
              label: row.readStatus ? '详情' : '已读并查看',
              type: 'text',
              icon: row.readStatus ? ACTION_ICON.VIEW : 'lucide:mail-check',
              onClick: onRead.bind(null, row),
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
