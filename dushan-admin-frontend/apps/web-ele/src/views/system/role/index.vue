<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemRoleApi } from '#/api/system/role';

import { ref } from 'vue';

import { confirm, Page, useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';
import { isEmpty } from '@vben/utils';

import { ElLoading, ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteRole,
  deleteRoleList,
  exportRole,
  getExportRoleFields,
  getRolePage,
  updateRoleStatus,
} from '#/api/system/role';
import { useExportModal } from '#/components';
import { DICT_TYPE } from '#/constants/dict-types';
import { useDictionary } from '#/services/dictionary/context';

import { useGridColumns, useGridFormSchema } from './data';
import AssignDataPermissionForm from './modules/assign-data-permission-form.vue';
import AssignMenuForm from './modules/assign-menu-form.vue';
import RoleForm from './modules/form.vue';

defineOptions({ name: 'SystemRole' });

const dictionary = useDictionary();

const [RoleFormModal, roleFormModalApi] = useVbenModal({
  connectedComponent: RoleForm,
  destroyOnClose: true,
});
const [AssignDataPermissionFormModal, assignDataPermissionFormModalApi] =
  useVbenModal({
    connectedComponent: AssignDataPermissionForm,
    destroyOnClose: true,
  });
const [AssignMenuFormModal, assignMenuFormModalApi] = useVbenModal({
  connectedComponent: AssignMenuForm,
  destroyOnClose: true,
});

const { ExportModal } = useExportModal();
const exportTableRef = ref();
const checkedIds = ref<string[]>([]);

function handleRefresh() {
  gridApi.query();
}

function onCreate() {
  roleFormModalApi.setData(null).open();
}

function onEdit(row: SystemRoleApi.RoleRespVO) {
  roleFormModalApi.setData(row).open();
}

function onAssignDataPermission(row: SystemRoleApi.RoleRespVO) {
  assignDataPermissionFormModalApi.setData(row).open();
}

function onAssignMenu(row: SystemRoleApi.RoleRespVO) {
  assignMenuFormModalApi.setData(row).open();
}

function handleExportSuccess() {
  ElMessage.success($t('ui.actionMessage.operationSuccess'));
}

async function onExport() {
  const fields = await getExportRoleFields();
  const formValues = await gridApi.formApi.getValues();

  exportTableRef.value?.setData({
    columns: fields,
    exportApi: exportRole,
    fileName: '角色数据.xls',
    searchParams: formValues,
  });
  exportTableRef.value?.open();
}

async function onDelete(row: SystemRoleApi.RoleRespVO) {
  const loadingInstance = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [row.name]),
  });

  try {
    await deleteRole(row.id);
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
    await deleteRoleList(checkedIds.value);
    checkedIds.value = [];
    ElMessage.success($t('ui.actionMessage.deleteSuccess'));
    handleRefresh();
  } finally {
    loadingInstance.close();
  }
}

async function handleStatusChange(
  newStatus: number,
  row: SystemRoleApi.RoleRespVO,
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
        await updateRoleStatus(row.id, newStatus);
        ElMessage.success($t('ui.actionMessage.operationSuccess'));
        resolve(true);
      })
      .catch(() => reject(new Error('取消')));
  });
}

function handleRowCheckboxChange({
  records,
}: {
  records: SystemRoleApi.RoleRespVO[];
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
    pagerConfig: {},
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          return await getRolePage({
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
  } as VxeTableGridOptions<SystemRoleApi.RoleRespVO>,
});
</script>

<template>
  <Page auto-content-height>
    <RoleFormModal @success="handleRefresh" />
    <AssignDataPermissionFormModal @success="handleRefresh" />
    <AssignMenuFormModal @success="handleRefresh" />
    <ExportModal ref="exportTableRef" @success="handleExportSuccess" />

    <Grid table-title="角色管理">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.create', ['角色']),
              type: 'primary',
              icon: ACTION_ICON.ADD,
              auth: ['system:permission:role:create'],
              onClick: onCreate,
            },
            {
              label: $t('ui.actionTitle.export'),
              type: 'primary',
              icon: ACTION_ICON.DOWNLOAD,
              auth: ['system:permission:role:export'],
              onClick: onExport,
            },
            {
              label: $t('ui.actionTitle.deleteBatch'),
              type: 'danger',
              icon: ACTION_ICON.DELETE,
              disabled: isEmpty(checkedIds),
              auth: ['system:permission:role:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [
                  `${checkedIds.length}个角色`,
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
              auth: ['system:permission:role:update'],
              onClick: onEdit.bind(null, row),
            },
            {
              label: $t('common.delete'),
              type: 'text',
              danger: true,
              icon: ACTION_ICON.DELETE,
              auth: ['system:permission:role:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [row.name]),
                confirm: onDelete.bind(null, row),
              },
            },
          ]"
          :drop-down-actions="[
            {
              label: '数据权限',
              icon: 'lucide:database',
              auth: ['system:permission:assign-role-data-scope'],
              onClick: onAssignDataPermission.bind(null, row),
            },
            {
              label: '菜单权限',
              icon: 'lucide:shield-check',
              auth: ['system:permission:assign-role-menu'],
              onClick: onAssignMenu.bind(null, row),
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
