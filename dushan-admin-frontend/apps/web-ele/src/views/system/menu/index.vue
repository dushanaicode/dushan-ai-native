<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemMenuApi } from '#/api/system/menu';

import { ref } from 'vue';

import { confirm, Page, useVbenModal } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';
import { $t } from '@vben/locales';
import { isEmpty } from '@vben/utils';

import { ElLoading, ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteMenu,
  deleteMenuList,
  getMenuList,
  updateMenuStatus,
} from '#/api/system/menu';
import { DICT_TYPE } from '#/constants/dict-types';
import { useDictionary } from '#/services/dictionary/context';

import { useGridColumns, useGridFormSchema } from './data';
import MenuForm from './modules/form.vue';

defineOptions({ name: 'SystemMenu' });

interface MenuTableRow extends SystemMenuApi.MenuRespVO {
  children?: MenuTableRow[];
}

const dictionary = useDictionary();

const [MenuFormModal, menuFormModalApi] = useVbenModal({
  connectedComponent: MenuForm,
  destroyOnClose: true,
});

const checkedIds = ref<string[]>([]);
const isExpanded = ref(true);

function handleRefresh() {
  gridApi.query();
}

function toggleExpand() {
  isExpanded.value = !isExpanded.value;
  gridApi.grid.setAllTreeExpand(isExpanded.value);
}

function onCreate() {
  menuFormModalApi
    .setData({
      kind: 'group',
      parentId: '0',
    })
    .open();
}

function getAppendMenuKind(row: SystemMenuApi.MenuRespVO) {
  if (row.kind === 'group') {
    return 'page';
  }
  return 'action';
}

function canAppend(row: SystemMenuApi.MenuRespVO) {
  return row.kind === 'group' || row.kind === 'page';
}

function getMenuIcon(row: SystemMenuApi.MenuRespVO) {
  if (row.kind === 'action') {
    return 'carbon:square-outline';
  }
  if (row.kind === 'link') {
    return 'carbon:link';
  }
  if (row.kind === 'iframe') {
    return 'carbon:application-web';
  }
  return row.icon || '';
}

function hasChildren(row: SystemMenuApi.MenuRespVO) {
  return !!(row as MenuTableRow).children?.length;
}

function onAppend(row: SystemMenuApi.MenuRespVO) {
  menuFormModalApi
    .setData({
      kind: getAppendMenuKind(row),
      parentId: row.id,
    })
    .open();
}

function onEdit(row: SystemMenuApi.MenuRespVO) {
  menuFormModalApi.setData(row).open();
}

async function onDelete(row: SystemMenuApi.MenuRespVO) {
  const loadingInstance = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [row.name]),
  });

  try {
    await deleteMenu(row.id);
    ElMessage.success($t('ui.actionMessage.deleteSuccess', [row.name]));
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
    await deleteMenuList(checkedIds.value);
    checkedIds.value = [];
    ElMessage.success($t('ui.actionMessage.deleteSuccess'));
    handleRefresh();
  } finally {
    loadingInstance.close();
  }
}

async function handleStatusChange(
  newStatus: number,
  row: SystemMenuApi.MenuRespVO,
): Promise<boolean | undefined> {
  return new Promise((resolve, reject) => {
    const statusLabel = dictionary.getDictLabel(
      DICT_TYPE.COMMON_STATUS,
      newStatus,
    );
    confirm({
      content: `确认将【${row.name}】的状态切换为【${statusLabel}】？`,
    })
      .then(async () => {
        await updateMenuStatus(row.id, newStatus);
        ElMessage.success($t('ui.actionMessage.operationSuccess'));
        resolve(true);
      })
      .catch(() => reject(new Error('取消')));
  });
}

function handleRowCheckboxChange({ records }: { records: MenuTableRow[] }) {
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
    pagerConfig: {
      enabled: false,
    },
    proxyConfig: {
      ajax: {
        query: async (_params, formValues) => {
          return await getMenuList({
            ...formValues,
            paginate: false,
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
    treeConfig: {
      accordion: false,
      expandAll: true,
      parentField: 'parentId',
      rowField: 'id',
      transform: true,
    },
  } as VxeTableGridOptions<MenuTableRow>,
});
</script>

<template>
  <Page auto-content-height>
    <MenuFormModal @success="handleRefresh" />

    <Grid table-title="菜单管理">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.create', ['菜单']),
              type: 'primary',
              icon: ACTION_ICON.ADD,
              auth: ['system:permission:menu:create'],
              onClick: onCreate,
            },
            {
              label: isExpanded ? '收缩' : '展开',
              type: 'primary',
              icon: isExpanded
                ? 'lucide:fold-vertical'
                : 'lucide:unfold-vertical',
              onClick: toggleExpand,
            },
            {
              label: $t('ui.actionTitle.deleteBatch'),
              type: 'danger',
              icon: ACTION_ICON.DELETE,
              disabled: isEmpty(checkedIds),
              auth: ['system:permission:menu:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [
                  `${checkedIds.length}个菜单`,
                ]),
                confirm: onDeleteBatch,
              },
            },
          ]"
        />
      </template>

      <template #name="{ row }">
        <div class="flex min-w-0 items-center gap-2">
          <IconifyIcon
            v-if="getMenuIcon(row)"
            :icon="getMenuIcon(row)"
            class="size-4 shrink-0"
          />
          <span class="truncate">{{ $t(row.name) }}</span>
        </div>
      </template>

      <template #actions="{ row }">
        <TableAction
          :actions="[
            {
              label: '新增下级',
              type: 'text',
              icon: ACTION_ICON.ADD,
              auth: ['system:permission:menu:create'],
              ifShow: canAppend(row),
              onClick: onAppend.bind(null, row),
            },
            {
              label: $t('common.edit'),
              type: 'text',
              icon: ACTION_ICON.EDIT,
              auth: ['system:permission:menu:update'],
              onClick: onEdit.bind(null, row),
            },
            {
              label: $t('common.delete'),
              type: 'text',
              danger: true,
              icon: ACTION_ICON.DELETE,
              auth: ['system:permission:menu:delete'],
              disabled: hasChildren(row),
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [row.name]),
                confirm: onDelete.bind(null, row),
              },
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
