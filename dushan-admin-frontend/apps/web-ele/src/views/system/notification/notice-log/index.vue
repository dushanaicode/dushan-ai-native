<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemNoticeLogApi } from '#/api/system/notification/notice-log';

import { useRoute } from 'vue-router';

import { Page, useVbenModal } from '@vben/common-ui';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import { getNoticeLogPage } from '#/api/system/notification/notice-log';

import { useGridColumns, useGridFormSchema } from './data';
import NoticeLogDetail from './modules/detail.vue';

defineOptions({ name: 'SystemNoticeLog' });

const route = useRoute();

const [DetailModal, detailModalApi] = useVbenModal({
  connectedComponent: NoticeLogDetail,
  destroyOnClose: true,
});

function getRouteNoticeId() {
  const rawValue = Array.isArray(route.query.noticeId)
    ? route.query.noticeId[0]
    : route.query.noticeId;
  const value = Number(rawValue);
  return rawValue && Number.isFinite(value) ? value : undefined;
}

function onDetail(row: SystemNoticeLogApi.NoticeLogRespVO) {
  detailModalApi.setData(row).open();
}

const [Grid] = useVbenVxeGrid({
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
          return await getNoticeLogPage({
            ...formValues,
            noticeId: formValues.noticeId ?? getRouteNoticeId(),
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
  } as VxeTableGridOptions<SystemNoticeLogApi.NoticeLogRespVO>,
});
</script>

<template>
  <Page auto-content-height>
    <DetailModal />

    <Grid table-title="推送日志">
      <template #actions="{ row }">
        <TableAction
          :actions="[
            {
              label: '详情',
              type: 'text',
              icon: ACTION_ICON.VIEW,
              auth: ['system:notification:log:query'],
              onClick: onDetail.bind(null, row),
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
