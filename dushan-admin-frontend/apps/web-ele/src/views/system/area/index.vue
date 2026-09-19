<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemAreaApi } from '#/api/system/area';

import { ref } from 'vue';

import { Page, useVbenModal } from '@vben/common-ui';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import { getAreaTree } from '#/api/system/area';

import { useGridColumns } from './data';
import IpQueryForm from './modules/form.vue';

defineOptions({ name: 'SystemArea' });

const [IpQueryFormModal, ipQueryFormModalApi] = useVbenModal({
  connectedComponent: IpQueryForm,
  destroyOnClose: true,
});

const isExpanded = ref(true);

function toggleExpand() {
  isExpanded.value = !isExpanded.value;
  gridApi.grid.setAllTreeExpand(isExpanded.value);
}

function handleQueryIp() {
  ipQueryFormModalApi.setData(null).open();
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
          return await getAreaTree();
        },
      },
    },
    rowConfig: {
      isHover: true,
      keyField: 'id',
    },
    toolbarConfig: {
      refresh: true,
    },
    treeConfig: {
      accordion: false,
      expandAll: true,
      reserve: true,
      rowField: 'id',
    },
  } as VxeTableGridOptions<SystemAreaApi.AreaNodeRespVO>,
});
</script>

<template>
  <Page auto-content-height>
    <IpQueryFormModal />

    <Grid table-title="地区列表">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: 'IP 查询',
              type: 'primary',
              icon: ACTION_ICON.SEARCH,
              onClick: handleQueryIp,
            },
            {
              label: isExpanded ? '收缩' : '展开',
              type: 'primary',
              icon: isExpanded
                ? 'lucide:fold-vertical'
                : 'lucide:unfold-vertical',
              onClick: toggleExpand,
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
