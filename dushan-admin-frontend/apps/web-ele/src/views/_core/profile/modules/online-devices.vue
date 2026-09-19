<script setup lang="tsx">
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { ProfileApi } from '#/api/core/profile';

import { confirm } from '@vben/common-ui';
import { formatDateTime } from '@vben/utils';

import { ElBadge, ElButton, ElMessage } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getUserOnlineDevices, kickoutOnlineDevice } from '#/api/core/profile';
import { $t } from '#/locales';

type DeviceRow = ProfileApi.ProfileOnlineDeviceVO;

async function handleKickout(row: DeviceRow) {
  if (row.isCurrent || !row.online) {
    return;
  }
  await confirm({
    content: `确认强制下线该设备吗？设备：${row.deviceName || row.tokenId}`,
  });
  await kickoutOnlineDevice(row.tokenId);
  ElMessage.success($t('ui.actionMessage.operationSuccess'));
  await gridApi.reload();
}

function useGridColumns(): VxeTableGridOptions<DeviceRow>['columns'] {
  return [
    {
      field: 'deviceName',
      minWidth: 180,
      slots: {
        default: ({ row }: { row: DeviceRow }) => (
          <div class="flex items-center">
            <div>
              <div>{row.deviceName || '-'}</div>
              {row.isCurrent && (
                <span class="mt-1 inline-flex rounded-sm bg-green-500 px-1.5 py-0.5 text-xs text-white">
                  当前设备
                </span>
              )}
            </div>
          </div>
        ),
      },
      title: '设备名称',
    },
    {
      field: 'ipAddress',
      minWidth: 150,
      slots: {
        default: ({ row }: { row: DeviceRow }) => (
          <div>
            <div>{row.ipAddress || '-'}</div>
            <div class="text-xs text-muted-foreground">
              {row.loginLocation || '-'}
            </div>
          </div>
        ),
      },
      title: 'IP 地址',
    },
    {
      field: 'browser',
      minWidth: 180,
      slots: {
        default: ({ row }: { row: DeviceRow }) => (
          <div>
            <div>{row.browser || '-'}</div>
            <div class="text-xs text-muted-foreground">{row.os || '-'}</div>
          </div>
        ),
      },
      title: '浏览器 / 系统',
    },
    {
      field: 'loginTime',
      formatter: ({ cellValue }) => String(formatDateTime(cellValue) || '-'),
      minWidth: 170,
      title: '登录时间',
    },
    {
      align: 'center',
      field: 'online',
      slots: {
        default: ({ row }: { row: DeviceRow }) => (
          <ElBadge
            type={row.online ? 'success' : 'info'}
            value={row.online ? '在线' : '离线'}
          />
        ),
      },
      title: '状态',
      width: 100,
    },
    {
      align: 'center',
      fixed: 'right',
      slots: {
        default: ({ row }: { row: DeviceRow }) =>
          !row.isCurrent && row.online ? (
            <ElButton link onClick={() => handleKickout(row)} type="danger">
              踢出
            </ElButton>
          ) : (
            <span>-</span>
          ),
      },
      title: '操作',
      width: 100,
    },
  ];
}

const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: {
    columns: useGridColumns(),
    height: 'auto',
    keepSource: true,
    pagerConfig: {
      enabled: false,
    },
    proxyConfig: {
      ajax: {
        query: async () => {
          const list = await getUserOnlineDevices();
          return {
            list,
            total: list.length,
          };
        },
      },
    },
    rowConfig: {
      height: 64,
      keyField: 'tokenId',
    },
    toolbarConfig: {
      enabled: false,
    },
  } as VxeTableGridOptions<DeviceRow>,
});
</script>

<template>
  <Grid />
</template>
