<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemDeptApi } from '#/api/system/dept';
import type { SystemUserApi } from '#/api/system/user';

import { onMounted, ref } from 'vue';

import { confirm, Page, useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';
import { isEmpty } from '@vben/utils';

import { ElLoading, ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteDept,
  deleteDeptList,
  getDeptList,
  updateDeptStatus,
} from '#/api/system/dept';
import { getSimpleUserList } from '#/api/system/user';
import { DICT_TYPE } from '#/constants/dict-types';
import { useDictionary } from '#/services/dictionary/context';

import { useGridColumns, useGridFormSchema } from './data';
import DeptForm from './modules/form.vue';

defineOptions({ name: 'SystemDept' });

const dictionary = useDictionary();

const [DeptFormModal, deptFormModalApi] = useVbenModal({
  connectedComponent: DeptForm,
  destroyOnClose: true,
});

interface DeptTableRow extends SystemDeptApi.DeptRespVO {
  children?: DeptTableRow[];
}

const checkedIds = ref<string[]>([]);
const isExpanded = ref(true);
const userList = ref<SystemUserApi.UserSimpleRespVO[]>([]);

function getLeaderName(userId?: string) {
  if (!userId) return undefined;
  return userList.value.find((user) => user.id === userId)?.nickname;
}

function handleRefresh() {
  gridApi.query();
}

function toggleExpand() {
  isExpanded.value = !isExpanded.value;
  gridApi.grid.setAllTreeExpand(isExpanded.value);
}

function onCreate() {
  deptFormModalApi.setData(null).open();
}

function onAppend(row: SystemDeptApi.DeptRespVO) {
  deptFormModalApi.setData({ parentId: row.id }).open();
}

function onEdit(row: SystemDeptApi.DeptRespVO) {
  deptFormModalApi.setData(row).open();
}

async function onDelete(row: SystemDeptApi.DeptRespVO) {
  const loadingInstance = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [row.name]),
  });

  try {
    await deleteDept(row.id);
    ElMessage.success($t('ui.actionMessage.deleteSuccess', [row.name]));
    handleRefresh();
  } finally {
    loadingInstance.close();
  }
}

async function handleStatusChange(
  newStatus: number,
  row: SystemDeptApi.DeptRespVO,
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
        await updateDeptStatus(row.id, newStatus);
        ElMessage.success($t('ui.actionMessage.operationSuccess'));
        resolve(true);
      })
      .catch(() => reject(new Error('取消')));
  });
}

async function onDeleteBatch() {
  const loadingInstance = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting'),
  });

  try {
    await deleteDeptList(checkedIds.value);
    checkedIds.value = [];
    ElMessage.success($t('ui.actionMessage.deleteSuccess'));
    handleRefresh();
  } finally {
    loadingInstance.close();
  }
}

function handleRowCheckboxChange({
  records,
}: {
  records: SystemDeptApi.DeptRespVO[];
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
    columns: useGridColumns(getLeaderName, handleStatusChange),
    height: 'auto',
    keepSource: true,
    pagerConfig: {
      enabled: false,
    },
    proxyConfig: {
      ajax: {
        query: async (_params, formValues) => {
          return await getDeptList(formValues);
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
  } as VxeTableGridOptions<SystemDeptApi.DeptRespVO>,
});

onMounted(async () => {
  userList.value = await getSimpleUserList();
});
</script>

<template>
  <Page auto-content-height>
    <DeptFormModal @success="handleRefresh" />

    <Grid table-title="部门管理">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.create', ['部门']),
              type: 'primary',
              icon: ACTION_ICON.ADD,
              auth: ['system:dept:create'],
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
              auth: ['system:dept:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [
                  `${checkedIds.length}个部门`,
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
              label: '新增下级',
              type: 'text',
              icon: ACTION_ICON.ADD,
              auth: ['system:dept:create'],
              onClick: onAppend.bind(null, row),
            },
            {
              label: $t('common.edit'),
              type: 'text',
              icon: ACTION_ICON.EDIT,
              auth: ['system:dept:update'],
              onClick: onEdit.bind(null, row),
            },
            {
              label: $t('common.delete'),
              type: 'text',
              danger: true,
              icon: ACTION_ICON.DELETE,
              auth: ['system:dept:delete'],
              disabled: !!(row as DeptTableRow).children?.length,
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
