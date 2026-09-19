<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraOnlineApi } from '#/api/infra/online';

import { computed } from 'vue';

import { useAccess } from '@vben/access';
import { Page } from '@vben/common-ui';

import { ElLoading, ElMessage } from 'element-plus';

import { TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import { forceLogout, getOnlineList } from '#/api/infra/online';

import {
  ONLINE_FORCE_LOGOUT_PERMISSION,
  useGridColumns,
  useGridFormSchema,
} from './data';

defineOptions({ name: 'InfraOnline' });

const { hasAccessByCodes } = useAccess();
const canForceLogout = computed(() =>
  hasAccessByCodes([ONLINE_FORCE_LOGOUT_PERMISSION]),
);

function handleRefresh() {
  gridApi.query();
}

function normalizeSearchParams(
  formValues: Record<string, unknown>,
  page: { currentPage: number; pageSize: number },
): InfraOnlineApi.OnlineInfoReqVO {
  return {
    ipaddr:
      typeof formValues.ipaddr === 'string' ? formValues.ipaddr : undefined,
    page: page.currentPage,
    pageSize: page.pageSize,
    userName:
      typeof formValues.userName === 'string' ? formValues.userName : undefined,
  };
}

function getOnlineDisplayName(row: InfraOnlineApi.OnlineInfoRespVO) {
  return row.userName || row.tokenId || '在线用户';
}

function ensureForceLogoutAllowed(row: InfraOnlineApi.OnlineInfoRespVO) {
  if (!canForceLogout.value) {
    ElMessage.warning('当前账号没有强制下线权限');
    return false;
  }

  if (!row.tokenId) {
    ElMessage.warning('缺少会话编号，无法强制下线');
    return false;
  }

  return true;
}

/** 强退用户 */
async function handleForceLogout(row: InfraOnlineApi.OnlineInfoRespVO) {
  if (!ensureForceLogoutAllowed(row)) {
    return;
  }

  const displayName = getOnlineDisplayName(row);
  const loadingInstance = ElLoading.service({
    fullscreen: true,
    text: `正在强制下线 ${displayName}`,
  });

  try {
    const success = await forceLogout(row.tokenId ?? '');
    if (!success) {
      ElMessage.error(`【${displayName}】强退失败`);
      return;
    }
    ElMessage.success(`【${displayName}】强退成功`);
    handleRefresh();
  } finally {
    loadingInstance.close();
  }
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
          return await getOnlineList(normalizeSearchParams(formValues, page));
        },
      },
    },
    rowConfig: {
      keyField: 'tokenId',
    },
    toolbarConfig: {
      refresh: true,
      search: true,
    },
  } as VxeTableGridOptions<InfraOnlineApi.OnlineInfoRespVO>,
});
</script>

<template>
  <Page auto-content-height>
    <template #doc>
      <DocAlert
        title="在线用户监控"
        url="https://doc.iocoder.cn/monitor/online/"
      />
    </template>

    <Grid table-title="在线用户">
      <template #actions="{ row }">
        <TableAction
          :actions="[
            {
              label: '强退',
              type: 'text',
              danger: true,
              icon: 'lucide:log-out',
              auth: [ONLINE_FORCE_LOGOUT_PERMISSION],
              disabled: !row.tokenId,
              popConfirm: {
                title: `确定要强制退出【${getOnlineDisplayName(row)}】吗？`,
                confirm: handleForceLogout.bind(null, row),
              },
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
