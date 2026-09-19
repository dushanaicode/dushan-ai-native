<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemAnnouncementApi } from '#/api/system/announcement';

import { ref } from 'vue';

import { confirm, Page, useVbenModal } from '@vben/common-ui';
import { isEmpty } from '@vben/utils';

import { ElLoading, ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteAnnouncement,
  deleteAnnouncementList,
  getAnnouncementPage,
  publishAnnouncement,
  scheduleAnnouncement,
} from '#/api/system/announcement';
import { $t } from '#/locales';

import { useGridColumns, useGridFormSchema } from './data';
import AnnouncementForm from './modules/form.vue';
import AnnouncementPreview from './modules/preview.vue';

defineOptions({ name: 'SystemAnnouncement' });

const ANNOUNCEMENT_STATUS_DRAFT = 0;
const ANNOUNCEMENT_STATUS_WAIT_PUBLISH = 1;

const checkedIds = ref<string[]>([]);

const [AnnouncementFormModal, announcementFormModalApi] = useVbenModal({
  connectedComponent: AnnouncementForm,
  destroyOnClose: true,
});

const [PreviewModal, previewModalApi] = useVbenModal({
  connectedComponent: AnnouncementPreview,
  destroyOnClose: true,
});

function handleRefresh() {
  gridApi.query();
}

function onCreate() {
  announcementFormModalApi.setData(null).open();
}

function onEdit(row: SystemAnnouncementApi.AnnouncementRespVO) {
  announcementFormModalApi.setData(row).open();
}

function onPreview(row: SystemAnnouncementApi.AnnouncementRespVO) {
  previewModalApi.setData(row).open();
}

async function onDelete(row: SystemAnnouncementApi.AnnouncementRespVO) {
  const loadingInstance = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [row.title]),
  });

  try {
    await deleteAnnouncement(row.id);
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
    await deleteAnnouncementList(checkedIds.value);
    checkedIds.value = [];
    ElMessage.success($t('ui.actionMessage.deleteSuccess'));
    handleRefresh();
  } finally {
    loadingInstance.close();
  }
}

async function runStatusAction(action: () => Promise<unknown>, text: string) {
  const loadingInstance = ElLoading.service({
    fullscreen: true,
    text,
  });

  try {
    await action();
    ElMessage.success($t('ui.actionMessage.operationSuccess'));
    handleRefresh();
  } finally {
    loadingInstance.close();
  }
}

function onPublish(row: SystemAnnouncementApi.AnnouncementRespVO) {
  confirm({
    content: `确认立即发布公告【${row.title}】？`,
  })
    .then(() =>
      runStatusAction(() => publishAnnouncement(row.id), '正在发布公告'),
    )
    .catch(() => undefined);
}

function onSchedule(row: SystemAnnouncementApi.AnnouncementRespVO) {
  if (!row.publishTime) {
    ElMessage.warning('请先设置未来的发布时间');
    return;
  }

  confirm({
    content: `确认将公告【${row.title}】设置为定时发布？`,
  })
    .then(() =>
      runStatusAction(() => scheduleAnnouncement(row.id), '正在设置定时发布'),
    )
    .catch(() => undefined);
}

function handleRowCheckboxChange({
  records,
}: {
  records: SystemAnnouncementApi.AnnouncementRespVO[];
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
          return await getAnnouncementPage({
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
  } as VxeTableGridOptions<SystemAnnouncementApi.AnnouncementRespVO>,
});
</script>

<template>
  <Page auto-content-height>
    <AnnouncementFormModal @success="handleRefresh" />
    <PreviewModal />

    <Grid table-title="公告管理">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.create', ['公告']),
              type: 'primary',
              icon: ACTION_ICON.ADD,
              auth: ['system:announcement:create'],
              onClick: onCreate,
            },
            {
              label: $t('ui.actionTitle.deleteBatch'),
              type: 'danger',
              icon: ACTION_ICON.DELETE,
              disabled: isEmpty(checkedIds),
              auth: ['system:announcement:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [
                  `${checkedIds.length}个公告`,
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
              label: '预览',
              type: 'text',
              icon: ACTION_ICON.VIEW,
              auth: ['system:announcement:query'],
              onClick: onPreview.bind(null, row),
            },
            {
              label: $t('common.edit'),
              type: 'text',
              icon: ACTION_ICON.EDIT,
              auth: ['system:announcement:update'],
              onClick: onEdit.bind(null, row),
            },
            {
              label: $t('common.delete'),
              type: 'text',
              danger: true,
              icon: ACTION_ICON.DELETE,
              auth: ['system:announcement:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [row.title]),
                confirm: onDelete.bind(null, row),
              },
            },
          ]"
          :drop-down-actions="[
            {
              label: '立即发布',
              icon: 'lucide:send',
              auth: ['system:announcement:update'],
              disabled:
                row.status !== ANNOUNCEMENT_STATUS_DRAFT &&
                row.status !== ANNOUNCEMENT_STATUS_WAIT_PUBLISH,
              onClick: onPublish.bind(null, row),
            },
            {
              label: '定时发布',
              icon: 'lucide:clock-3',
              auth: ['system:announcement:update'],
              disabled: row.status !== ANNOUNCEMENT_STATUS_DRAFT,
              onClick: onSchedule.bind(null, row),
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
