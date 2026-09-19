<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemDictTypeApi } from '#/api/system/dict/type';

import { ref } from 'vue';

import { confirm, useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';
import { isEmpty } from '@vben/utils';

import { ElLoading, ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteDictType,
  deleteDictTypeList,
  exportDictType,
  getDictTypePage,
  getExportDictTypeFields,
  updateDictTypeStatus,
} from '#/api/system/dict/type';
import { useExportModal } from '#/components';
import { DICT_TYPE } from '#/constants/dict-types';
import { useDictionary } from '#/services/dictionary/context';

import { useTypeGridColumns, useTypeGridFormSchema } from '../data';
import TypeForm from './type-form.vue';

const emit = defineEmits<{
  select: [dictType: string];
}>();

const dictionary = useDictionary();

const [TypeFormModal, typeFormModalApi] = useVbenModal({
  connectedComponent: TypeForm,
  destroyOnClose: true,
});

const { ExportModal } = useExportModal();
const exportTableRef = ref();
const checkedIds = ref<string[]>([]);

function handleRefresh() {
  gridApi.query();
}

async function onExport() {
  const fields = await getExportDictTypeFields();
  const formValues = await gridApi.formApi.getValues();

  exportTableRef.value?.setData({
    columns: fields,
    exportApi: exportDictType,
    fileName: '字典类型.xls',
    searchParams: formValues,
  });
  exportTableRef.value?.open();
}

function handleExportSuccess() {
  ElMessage.success($t('ui.actionMessage.operationSuccess'));
}

function onCreate() {
  typeFormModalApi.setData(null).open();
}

function onEdit(row: SystemDictTypeApi.DictTypeRespVO) {
  typeFormModalApi.setData(row).open();
}

async function onDelete(row: SystemDictTypeApi.DictTypeRespVO) {
  const loadingInstance = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [row.name]),
  });

  try {
    await deleteDictType(row.id);
    ElMessage.success($t('ui.actionMessage.deleteSuccess', [row.name]));
    handleRefresh();
  } finally {
    loadingInstance.close();
  }
}

async function handleStatusChange(
  newStatus: number,
  row: SystemDictTypeApi.DictTypeRespVO,
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
        await updateDictTypeStatus(row.id, newStatus);
        ElMessage.success($t('ui.actionMessage.operationSuccess'));
        resolve(true);
      })
      .catch(() => reject(new Error('取消')));
  });
}

async function onDeleteBatch() {
  await deleteDictTypeList(checkedIds.value);
  checkedIds.value = [];
  ElMessage.success($t('ui.actionMessage.deleteSuccess'));
  handleRefresh();
}

function handleRowCheckboxChange({
  records,
}: {
  records: SystemDictTypeApi.DictTypeRespVO[];
}) {
  checkedIds.value = records.map((item) => item.id);
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useTypeGridFormSchema(),
  },
  gridEvents: {
    cellClick: ({ row }: { row: SystemDictTypeApi.DictTypeRespVO }) => {
      emit('select', row.type);
    },
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
          return await getDictTypePage({
            ...formValues,
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
  } as VxeTableGridOptions<SystemDictTypeApi.DictTypeRespVO>,
});
</script>

<template>
  <div class="h-full">
    <TypeFormModal @success="handleRefresh" />
    <ExportModal ref="exportTableRef" @success="handleExportSuccess" />

    <Grid table-title="字典类型">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.create', ['字典类型']),
              type: 'primary',
              icon: ACTION_ICON.ADD,
              auth: ['system:dict:create'],
              onClick: onCreate,
            },
            {
              label: $t('ui.actionTitle.export'),
              type: 'primary',
              icon: ACTION_ICON.DOWNLOAD,
              auth: ['system:dict:export'],
              onClick: onExport,
            },
            {
              label: $t('ui.actionTitle.deleteBatch'),
              type: 'danger',
              icon: ACTION_ICON.DELETE,
              disabled: isEmpty(checkedIds),
              auth: ['system:dict:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [
                  `${checkedIds.length}个字典类型`,
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
              auth: ['system:dict:update'],
              onClick: onEdit.bind(null, row),
            },
            {
              label: $t('common.delete'),
              type: 'text',
              danger: true,
              icon: ACTION_ICON.DELETE,
              auth: ['system:dict:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [row.name]),
                confirm: onDelete.bind(null, row),
              },
            },
          ]"
        />
      </template>
    </Grid>
  </div>
</template>
