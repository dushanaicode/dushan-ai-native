<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraConfigTypeApi } from '#/api/infra/config/type';

import { ref } from 'vue';

import { confirm, useVbenModal } from '@vben/common-ui';
import { isEmpty } from '@vben/utils';

import { ElLoading, ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import { getConfigDataPage } from '#/api/infra/config/data';
import {
  deleteConfigType,
  deleteConfigTypeList,
  exportConfigType,
  getConfigTypePage,
  getExportConfigTypeFields,
  updateConfigTypeStatus,
} from '#/api/infra/config/type';
import { useExportModal } from '#/components';
import { DICT_TYPE } from '#/constants/dict-types';
import { $t } from '#/locales';
import { useDictionary } from '#/services/dictionary/context';

import { useTypeGridColumns, useTypeGridFormSchema } from '../data';
import TypeForm from './type-form.vue';

const emit = defineEmits<{
  select: [typeId?: string];
}>();

const dictionary = useDictionary();

const [TypeFormModal, typeFormModalApi] = useVbenModal({
  connectedComponent: TypeForm,
  destroyOnClose: true,
});

const { ExportModal } = useExportModal();
const exportTableRef = ref();
const checkedIds = ref<string[]>([]);
const checkedRows = ref<InfraConfigTypeApi.ConfigTypeRespVO[]>([]);

function toOptionalNumber(value: unknown) {
  if (value === undefined || value === null || value === '') {
    return undefined;
  }
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : undefined;
}

function normalizeSearchParams(
  values: Record<string, unknown>,
): InfraConfigTypeApi.ConfigTypePageReqVO {
  return {
    code: typeof values.code === 'string' ? values.code : undefined,
    createTime: Array.isArray(values.createTime)
      ? values.createTime
      : undefined,
    module: typeof values.module === 'string' ? values.module : undefined,
    name: typeof values.name === 'string' ? values.name : undefined,
    status: toOptionalNumber(values.status),
  };
}

function handleRefresh() {
  checkedIds.value = [];
  checkedRows.value = [];
  gridApi.query();
}

function handleCreate() {
  typeFormModalApi.setData(null).open();
}

function handleEdit(row: InfraConfigTypeApi.ConfigTypeRespVO) {
  typeFormModalApi.setData(row).open();
}

async function handleExport() {
  const fields = await getExportConfigTypeFields();
  const formValues = await gridApi.formApi.getValues();

  exportTableRef.value?.setData({
    columns: fields,
    exportApi: exportConfigType,
    fileName: '配置类型.xls',
    searchParams: normalizeSearchParams(formValues),
  });
  exportTableRef.value?.open();
}

function handleExportSuccess() {
  ElMessage.success($t('ui.actionMessage.operationSuccess'));
}

async function handleStatusChange(
  newStatus: number,
  row: InfraConfigTypeApi.ConfigTypeRespVO,
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
        const loading = ElLoading.service({
          fullscreen: true,
          text: $t('ui.actionMessage.updating', [row.name]),
        });

        try {
          if (!row.id) {
            resolve(false);
            return;
          }
          await updateConfigTypeStatus(row.id, newStatus);
          ElMessage.success($t('ui.actionMessage.operationSuccess'));
          resolve(true);
        } finally {
          loading.close();
        }
      })
      .catch(() => reject(new Error('取消')));
  });
}

async function findTypesWithConfigData(
  rows: InfraConfigTypeApi.ConfigTypeRespVO[],
) {
  const typeNames: string[] = [];

  for (const row of rows) {
    if (!row.id) {
      continue;
    }

    const result = await getConfigDataPage({
      page: 1,
      pageSize: 1,
      typeId: row.id,
    });
    if (result.total > 0) {
      typeNames.push(row.name);
    }
  }

  return typeNames;
}

function getChildDataWarning(typeNames: string[]) {
  return `配置类型「${typeNames.join('、')}」下存在配置数据，请先删除配置数据`;
}

async function handleDelete(row: InfraConfigTypeApi.ConfigTypeRespVO) {
  const loading = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [row.name]),
  });

  try {
    const typeNames = await findTypesWithConfigData([row]);
    if (typeNames.length > 0) {
      ElMessage.warning(getChildDataWarning(typeNames));
      return;
    }

    if (!row.id) {
      return;
    }
    await deleteConfigType(row.id);
    ElMessage.success($t('ui.actionMessage.deleteSuccess', [row.name]));
    emit('select', undefined);
    handleRefresh();
  } finally {
    loading.close();
  }
}

async function handleDeleteBatch() {
  const loading = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [
      `${checkedIds.value.length}个配置类型`,
    ]),
  });

  try {
    const typeNames = await findTypesWithConfigData(checkedRows.value);
    if (typeNames.length > 0) {
      ElMessage.warning(getChildDataWarning(typeNames));
      return;
    }

    await deleteConfigTypeList(checkedIds.value);
    ElMessage.success($t('ui.actionMessage.deleteSuccess'));
    emit('select', undefined);
    handleRefresh();
  } finally {
    loading.close();
  }
}

function handleRowCheckboxChange({
  records,
}: {
  records: InfraConfigTypeApi.ConfigTypeRespVO[];
}) {
  checkedRows.value = records;
  checkedIds.value = checkedRows.value
    .map((item) => item.id)
    .filter((id): id is string => id !== null && id !== undefined);
}

function handleCellClick({
  column,
  row,
}: {
  column?: { field?: string; type?: string };
  row: InfraConfigTypeApi.ConfigTypeRespVO;
}) {
  if (column?.field === 'operation' || column?.type === 'checkbox') {
    return;
  }

  emit('select', row.id ?? undefined);
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useTypeGridFormSchema(),
  },
  gridEvents: {
    cellClick: handleCellClick,
    checkboxAll: handleRowCheckboxChange,
    checkboxChange: handleRowCheckboxChange,
  },
  gridOptions: {
    columns: useTypeGridColumns(handleStatusChange),
    height: 'auto',
    keepSource: true,
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          return await getConfigTypePage({
            ...normalizeSearchParams(formValues),
            page: page.currentPage,
            pageSize: page.pageSize,
          });
        },
      },
    },
    rowConfig: {
      isCurrent: true,
      keyField: 'id',
    },
    toolbarConfig: {
      refresh: true,
      search: true,
    },
  } as VxeTableGridOptions<InfraConfigTypeApi.ConfigTypeRespVO>,
});
</script>

<template>
  <div class="h-full">
    <TypeFormModal @success="handleRefresh" />
    <ExportModal ref="exportTableRef" @success="handleExportSuccess" />

    <Grid table-title="配置类型">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.create', ['配置类型']),
              type: 'primary',
              icon: ACTION_ICON.ADD,
              auth: ['infra:config:type:create'],
              onClick: handleCreate,
            },
            {
              label: $t('ui.actionTitle.export'),
              type: 'primary',
              icon: ACTION_ICON.DOWNLOAD,
              auth: ['infra:config:type:export'],
              onClick: handleExport,
            },
            {
              label: $t('ui.actionTitle.deleteBatch'),
              type: 'danger',
              icon: ACTION_ICON.DELETE,
              disabled: isEmpty(checkedIds),
              auth: ['infra:config:type:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [
                  `${checkedIds.length}个配置类型`,
                ]),
                confirm: handleDeleteBatch,
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
              auth: ['infra:config:type:update'],
              onClick: handleEdit.bind(null, row),
            },
            {
              label: $t('common.delete'),
              type: 'text',
              danger: true,
              icon: ACTION_ICON.DELETE,
              auth: ['infra:config:type:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [row.name]),
                confirm: handleDelete.bind(null, row),
              },
            },
          ]"
        />
      </template>
    </Grid>
  </div>
</template>
