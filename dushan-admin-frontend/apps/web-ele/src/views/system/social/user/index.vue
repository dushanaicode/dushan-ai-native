<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemSocialUserApi } from '#/api/system/social/user';

import { Page, useVbenModal } from '@vben/common-ui';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import { getSocialUserPage } from '#/api/system/social/user';

import { useGridColumns, useGridFormSchema } from './data';
import SocialUserDetail from './modules/detail.vue';

defineOptions({ name: 'SystemSocialUser' });

const [SocialUserDetailModal, socialUserDetailModalApi] = useVbenModal({
  connectedComponent: SocialUserDetail,
  destroyOnClose: true,
});

function onDetail(row: SystemSocialUserApi.SocialUserRespVO) {
  socialUserDetailModalApi.setData(row).open();
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
          return await getSocialUserPage({
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
  } as VxeTableGridOptions<SystemSocialUserApi.SocialUserRespVO>,
});
</script>

<template>
  <Page auto-content-height>
    <SocialUserDetailModal />

    <Grid table-title="社交用户">
      <template #actions="{ row }">
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.detail'),
              type: 'text',
              icon: ACTION_ICON.VIEW,
              auth: ['system:social:user:query'],
              onClick: onDetail.bind(null, row),
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
