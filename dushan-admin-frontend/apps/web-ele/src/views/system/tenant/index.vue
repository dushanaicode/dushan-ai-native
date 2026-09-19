<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemTenantApi } from '#/api/system/tenant';
import type { SystemTenantPackageApi } from '#/api/system/tenant/package';

import { onMounted, ref } from 'vue';

import { confirm, Page, useVbenModal } from '@vben/common-ui';
import { isEmpty } from '@vben/utils';

import { ElLoading, ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteTenant,
  deleteTenantList,
  exportTenant,
  getExportTenantFields,
  getTenantPage,
  updateTenantStatus,
} from '#/api/system/tenant';
import { getSimpleTenantPackageList } from '#/api/system/tenant/package';
import { useExportModal } from '#/components';
import { DICT_TYPE } from '#/constants/dict-types';
import { $t } from '#/locales';
import { useDictionary } from '#/services/dictionary/context';

import { useGridColumns, useGridFormSchema } from './data';
import TenantForm from './modules/form.vue';

defineOptions({ name: 'SystemTenant' });

const dictionary = useDictionary();

const [TenantFormModal, tenantFormModalApi] = useVbenModal({
  connectedComponent: TenantForm,
  destroyOnClose: true,
});

const { ExportModal } = useExportModal();
const exportTableRef = ref();
const checkedIds = ref<string[]>([]);
const tenantPackages = ref<SystemTenantPackageApi.TenantPackageSimpleRespVO[]>(
  [],
);

function handleRefresh() {
  gridApi.query();
}

function getPackageName(packageId: string) {
  if (packageId === '0') {
    return '系统租户';
  }
  return tenantPackages.value.find((item) => item.id === packageId)?.name;
}

async function loadTenantPackages() {
  tenantPackages.value = await getSimpleTenantPackageList();
}

async function onExport() {
  const fields = await getExportTenantFields();
  const formValues = await gridApi.formApi.getValues();

  exportTableRef.value?.setData({
    columns: fields,
    exportApi: exportTenant,
    fileName: '租户数据.xls',
    searchParams: formValues,
  });
  exportTableRef.value?.open();
}

function handleExportSuccess() {
  ElMessage.success($t('ui.actionMessage.operationSuccess'));
}

function onCreate() {
  tenantFormModalApi.setData(null).open();
}

function onEdit(row: SystemTenantApi.TenantRespVO) {
  tenantFormModalApi.setData(row).open();
}

async function onDelete(row: SystemTenantApi.TenantRespVO) {
  const loadingInstance = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [row.name]),
  });

  try {
    await deleteTenant(row.id);
    ElMessage.success($t('ui.actionMessage.deleteSuccess', [row.name]));
    handleRefresh();
  } finally {
    loadingInstance.close();
  }
}

async function handleStatusChange(
  newStatus: number,
  row: SystemTenantApi.TenantRespVO,
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
        await updateTenantStatus(row.id, newStatus);
        ElMessage.success($t('ui.actionMessage.operationSuccess'));
        resolve(true);
      })
      .catch(() => reject(new Error('取消')));
  });
}

async function onDeleteBatch() {
  await deleteTenantList(checkedIds.value);
  checkedIds.value = [];
  ElMessage.success($t('ui.actionMessage.deleteSuccess'));
  handleRefresh();
}

function handleRowCheckboxChange({
  records,
}: {
  records: SystemTenantApi.TenantRespVO[];
}) {
  checkedIds.value = records.map((item) => item.id);
}

onMounted(() => {
  void loadTenantPackages();
});

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useGridFormSchema(),
  },
  gridEvents: {
    checkboxAll: handleRowCheckboxChange,
    checkboxChange: handleRowCheckboxChange,
  },
  gridOptions: {
    columns: useGridColumns(getPackageName, handleStatusChange),
    height: 'auto',
    keepSource: true,
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          return await getTenantPage({
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
  } as VxeTableGridOptions<SystemTenantApi.TenantRespVO>,
});
</script>

<template>
  <Page auto-content-height>
    <TenantFormModal @success="handleRefresh" />
    <ExportModal ref="exportTableRef" @success="handleExportSuccess" />

    <Grid table-title="租户管理">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.create', ['租户']),
              type: 'primary',
              icon: ACTION_ICON.ADD,
              auth: ['system:tenant:create'],
              onClick: onCreate,
            },
            {
              label: $t('ui.actionTitle.export'),
              type: 'primary',
              icon: ACTION_ICON.DOWNLOAD,
              auth: ['system:tenant:export'],
              onClick: onExport,
            },
            {
              label: $t('ui.actionTitle.deleteBatch'),
              type: 'danger',
              icon: ACTION_ICON.DELETE,
              disabled: isEmpty(checkedIds),
              auth: ['system:tenant:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [
                  `${checkedIds.length}个租户`,
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
              auth: ['system:tenant:update'],
              onClick: onEdit.bind(null, row),
            },
            {
              label: $t('common.delete'),
              type: 'text',
              danger: true,
              icon: ACTION_ICON.DELETE,
              auth: ['system:tenant:delete'],
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
