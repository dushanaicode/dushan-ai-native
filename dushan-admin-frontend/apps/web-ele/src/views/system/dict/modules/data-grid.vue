<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemDictDataApi } from '#/api/system/dict/data';

import { ref, watch } from 'vue';

import { confirm, useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';
import { isEmpty } from '@vben/utils';

import { ElLoading, ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteDictData,
  deleteDictDataList,
  exportDictData,
  getDictDataPage,
  getExportDictDataFields,
  updateDictDataStatus,
} from '#/api/system/dict/data';
import { useExportModal } from '#/components';
import TagPreview from '#/components/tag-preview.vue';
import { DICT_TYPE } from '#/constants/dict-types';
import { useDictionary } from '#/services/dictionary/context';

import { useDataGridColumns, useDataGridFormSchema } from '../data';
import DataForm from './data-form.vue';

const props = withDefaults(
  defineProps<{
    dictType?: string;
  }>(),
  {
    dictType: undefined,
  },
);

const dictionary = useDictionary();

const [DataFormModal, dataFormModalApi] = useVbenModal({
  connectedComponent: DataForm,
  destroyOnClose: true,
});

const { ExportModal } = useExportModal();
const exportTableRef = ref();
const checkedIds = ref<string[]>([]);

function handleRefresh() {
  gridApi.query();
}

async function onExport() {
  const fields = await getExportDictDataFields();
  const formValues = await gridApi.formApi.getValues();

  exportTableRef.value?.setData({
    columns: fields,
    exportApi: exportDictData,
    fileName: '字典数据.xls',
    searchParams: formValues,
  });
  exportTableRef.value?.open();
}

function handleExportSuccess() {
  ElMessage.success($t('ui.actionMessage.operationSuccess'));
}

function onCreate() {
  dataFormModalApi.setData({ dictType: props.dictType }).open();
}

function onEdit(row: SystemDictDataApi.DictDataRespVO) {
  dataFormModalApi.setData(row).open();
}

async function onDelete(row: SystemDictDataApi.DictDataRespVO) {
  const loadingInstance = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [row.label]),
  });

  try {
    await deleteDictData(row.id);
    ElMessage.success($t('ui.actionMessage.deleteSuccess', [row.label]));
    handleRefresh();
  } finally {
    loadingInstance.close();
  }
}

async function handleStatusChange(
  newStatus: number,
  row: SystemDictDataApi.DictDataRespVO,
): Promise<boolean | undefined> {
  return new Promise((resolve, reject) => {
    const statusLabel = dictionary.getDictLabel(
      DICT_TYPE.COMMON_STATUS,
      newStatus,
    );
    confirm({
      content: `确认将【${row.label}】的状态切换为【${statusLabel}】？`,
    })
      .then(async () => {
        await updateDictDataStatus(row.id, newStatus);
        ElMessage.success($t('ui.actionMessage.operationSuccess'));
        resolve(true);
      })
      .catch(() => reject(new Error('取消')));
  });
}

async function onDeleteBatch() {
  await deleteDictDataList(checkedIds.value);
  checkedIds.value = [];
  ElMessage.success($t('ui.actionMessage.deleteSuccess'));
  handleRefresh();
}

function handleRowCheckboxChange({
  records,
}: {
  records: SystemDictDataApi.DictDataRespVO[];
}) {
  checkedIds.value = records.map((item) => item.id);
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useDataGridFormSchema(),
  },
  gridEvents: {
    checkboxAll: handleRowCheckboxChange,
    checkboxChange: handleRowCheckboxChange,
  },
  gridOptions: {
    columns: useDataGridColumns(handleStatusChange),
    height: 'auto',
    keepSource: true,
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          return await getDictDataPage({
            ...formValues,
            dictType: props.dictType,
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
  } as VxeTableGridOptions<SystemDictDataApi.DictDataRespVO>,
});

watch(
  () => props.dictType,
  () => {
    if (props.dictType) {
      handleRefresh();
    }
  },
);
</script>

<template>
  <div class="flex h-full flex-col">
    <DataFormModal @success="handleRefresh" />
    <ExportModal ref="exportTableRef" @success="handleExportSuccess" />

    <Grid table-title="字典数据">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.create', ['字典数据']),
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
                  `${checkedIds.length}个字典数据`,
                ]),
                confirm: onDeleteBatch,
              },
            },
          ]"
        />
      </template>

      <template #colorType="{ row }">
        <TagPreview
          v-if="row.colorType"
          :color-type="row.colorType"
          :text="row.colorType"
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
                title: $t('ui.actionMessage.deleteConfirm', [row.label]),
                confirm: onDelete.bind(null, row),
              },
            },
          ]"
        />
      </template>
    </Grid>
  </div>
</template>
