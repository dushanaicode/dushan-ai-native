<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemDeptApi } from '#/api/system/dept';
import type { SystemUserApi } from '#/api/system/user';

import { ref } from 'vue';

import { confirm, Page, useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';
import { isEmpty } from '@vben/utils';

import { ElLoading, ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteUser,
  deleteUserList,
  exportUser,
  getExportUserFields,
  getUserPage,
  updateUserStatus,
} from '#/api/system/user';
import { useExportModal } from '#/components';
import { DICT_TYPE } from '#/constants/dict-types';
import { useDictionary } from '#/services/dictionary/context';

import { useGridColumns, useGridFormSchema } from './data';
import AssignRoleForm from './modules/assign-role-form.vue';
import DeptTree from './modules/dept-tree.vue';
import UserForm from './modules/form.vue';
import ImportForm from './modules/import-form.vue';
import ResetPasswordForm from './modules/reset-password-form.vue';

defineOptions({ name: 'SystemUser' });

const dictionary = useDictionary();

const [UserFormModal, userFormModalApi] = useVbenModal({
  connectedComponent: UserForm,
  destroyOnClose: true,
});
const [ResetPasswordFormModal, resetPasswordFormModalApi] = useVbenModal({
  connectedComponent: ResetPasswordForm,
  destroyOnClose: true,
});
const [AssignRoleFormModal, assignRoleFormModalApi] = useVbenModal({
  connectedComponent: AssignRoleForm,
  destroyOnClose: true,
});
const [ImportFormModal, importFormModalApi] = useVbenModal({
  connectedComponent: ImportForm,
  destroyOnClose: true,
});

const { ExportModal } = useExportModal();
const exportTableRef = ref();
const checkedIds = ref<string[]>([]);
const selectedDeptId = ref<string>();

function handleRefresh() {
  gridApi.query();
}

function onCreate() {
  userFormModalApi.setData(null).open();
}

function onImport() {
  importFormModalApi.open();
}

function handleExportSuccess() {
  ElMessage.success($t('ui.actionMessage.operationSuccess'));
}

function onEdit(row: SystemUserApi.UserRespVO) {
  userFormModalApi.setData(row).open();
}

function onResetPassword(row: SystemUserApi.UserRespVO) {
  resetPasswordFormModalApi.setData(row).open();
}

function onAssignRole(row: SystemUserApi.UserRespVO) {
  assignRoleFormModalApi.setData(row).open();
}

async function onDelete(row: SystemUserApi.UserRespVO) {
  const loadingInstance = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [row.username]),
  });

  try {
    await deleteUser(row.id);
    ElMessage.success($t('ui.actionMessage.deleteSuccess', [row.username]));
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
    await deleteUserList(checkedIds.value);
    checkedIds.value = [];
    ElMessage.success($t('ui.actionMessage.deleteSuccess'));
    handleRefresh();
  } finally {
    loadingInstance.close();
  }
}

async function handleStatusChange(
  newStatus: number,
  row: SystemUserApi.UserRespVO,
): Promise<boolean | undefined> {
  return new Promise((resolve, reject) => {
    const statusLabel = dictionary.getDictLabel(
      DICT_TYPE.COMMON_STATUS,
      newStatus,
    );
    confirm({
      content: `确认将【${row.username}】的状态切换为【${statusLabel}】？`,
    })
      .then(async () => {
        await updateUserStatus(row.id, newStatus);
        ElMessage.success($t('ui.actionMessage.operationSuccess'));
        resolve(true);
      })
      .catch(() => reject(new Error('取消')));
  });
}

function handleRowCheckboxChange({
  records,
}: {
  records: SystemUserApi.UserRespVO[];
}) {
  checkedIds.value = records.map((item) => item.id);
}

async function handleExport() {
  const columns = await getExportUserFields();
  const formValues = await gridApi.formApi.getValues();
  exportTableRef.value?.setData({
    columns,
    exportApi: exportUser,
    fileName: '用户数据.xls',
    searchParams: {
      ...formValues,
      deptId: selectedDeptId.value,
    },
  });
  exportTableRef.value?.open();
}

function handleDeptSelect(dept?: SystemDeptApi.DeptSimpleRespVO) {
  selectedDeptId.value = dept?.id;
  gridApi.query();
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
          return await getUserPage({
            ...formValues,
            deptId: selectedDeptId.value,
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
  } as VxeTableGridOptions<SystemUserApi.UserRespVO>,
});
</script>

<template>
  <Page auto-content-height>
    <UserFormModal @success="handleRefresh" />
    <ResetPasswordFormModal @success="handleRefresh" />
    <AssignRoleFormModal @success="handleRefresh" />
    <ImportFormModal @success="handleRefresh" />
    <ExportModal ref="exportTableRef" @success="handleExportSuccess" />

    <div class="flex h-full gap-4">
      <div class="h-full w-64 shrink-0">
        <DeptTree @select="handleDeptSelect" />
      </div>

      <div class="min-w-0 flex-1">
        <Grid table-title="用户管理">
          <template #toolbar-tools>
            <TableAction
              :actions="[
                {
                  label: $t('ui.actionTitle.create', ['用户']),
                  type: 'primary',
                  icon: ACTION_ICON.ADD,
                  auth: ['system:user:create'],
                  onClick: onCreate,
                },
                {
                  label: '导入',
                  type: 'primary',
                  icon: ACTION_ICON.UPLOAD,
                  auth: ['system:user:import'],
                  onClick: onImport,
                },
                {
                  label: '导出',
                  type: 'primary',
                  icon: ACTION_ICON.DOWNLOAD,
                  auth: ['system:user:export'],
                  onClick: handleExport,
                },
                {
                  label: $t('ui.actionTitle.deleteBatch'),
                  type: 'danger',
                  icon: ACTION_ICON.DELETE,
                  disabled: isEmpty(checkedIds),
                  auth: ['system:user:delete'],
                  popConfirm: {
                    title: $t('ui.actionMessage.deleteConfirm', [
                      `${checkedIds.length}个用户`,
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
                  auth: ['system:user:update'],
                  onClick: onEdit.bind(null, row),
                },
                {
                  label: $t('common.delete'),
                  type: 'text',
                  danger: true,
                  icon: ACTION_ICON.DELETE,
                  auth: ['system:user:delete'],
                  popConfirm: {
                    title: $t('ui.actionMessage.deleteConfirm', [row.username]),
                    confirm: onDelete.bind(null, row),
                  },
                },
              ]"
              :drop-down-actions="[
                {
                  label: '分配角色',
                  icon: 'lucide:shield-check',
                  auth: ['system:permission:assign-user-role'],
                  onClick: onAssignRole.bind(null, row),
                },
                {
                  label: '重置密码',
                  icon: 'lucide:key-round',
                  auth: ['system:user:update-password'],
                  onClick: onResetPassword.bind(null, row),
                },
              ]"
            />
          </template>
        </Grid>
      </div>
    </div>
  </Page>
</template>
