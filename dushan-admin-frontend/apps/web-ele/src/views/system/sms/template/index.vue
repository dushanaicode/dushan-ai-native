<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemSmsTemplateApi } from '#/api/system/sms/template';

import { ref } from 'vue';

import { confirm, Page, useVbenModal } from '@vben/common-ui';
import { isEmpty } from '@vben/utils';

import { ElLoading, ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  deleteSmsTemplate,
  deleteSmsTemplateList,
  exportSmsTemplate,
  getExportSmsTemplateFields,
  getSmsTemplatePage,
  updateSmsTemplateStatus,
} from '#/api/system/sms/template';
import { useExportModal } from '#/components';
import { DICT_TYPE } from '#/constants/dict-types';
import { $t } from '#/locales';
import { useDictionary } from '#/services/dictionary/context';

import { useGridColumns, useGridFormSchema } from './data';
import SmsTemplateForm from './modules/form.vue';
import SmsTemplateSendForm from './modules/send-form.vue';

defineOptions({ name: 'SystemSmsTemplate' });

const dictionary = useDictionary();

const [SmsTemplateFormModal, smsTemplateFormModalApi] = useVbenModal({
  connectedComponent: SmsTemplateForm,
  destroyOnClose: true,
});

const [SmsTemplateSendFormModal, smsTemplateSendFormModalApi] = useVbenModal({
  connectedComponent: SmsTemplateSendForm,
  destroyOnClose: true,
});

const { ExportModal } = useExportModal();
const exportTableRef = ref();
const checkedIds = ref<string[]>([]);

function handleRefresh() {
  gridApi.query();
}

function onCreate() {
  smsTemplateFormModalApi.setData(null).open();
}

function onEdit(row: SystemSmsTemplateApi.SmsTemplateRespVO) {
  smsTemplateFormModalApi.setData(row).open();
}

function onSend(row: SystemSmsTemplateApi.SmsTemplateRespVO) {
  smsTemplateSendFormModalApi.setData(row).open();
}

async function onExport() {
  const fields = await getExportSmsTemplateFields();
  const formValues = await gridApi.formApi.getValues();

  exportTableRef.value?.setData({
    columns: fields,
    exportApi: exportSmsTemplate,
    fileName: '短信模板数据.xls',
    searchParams: formValues,
  });
  exportTableRef.value?.open();
}

function handleExportSuccess() {
  ElMessage.success($t('ui.actionMessage.operationSuccess'));
}

async function onDelete(row: SystemSmsTemplateApi.SmsTemplateRespVO) {
  if (!row.id) {
    return;
  }
  const loadingInstance = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [row.name]),
  });

  try {
    await deleteSmsTemplate(row.id);
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
    await deleteSmsTemplateList(checkedIds.value);
    checkedIds.value = [];
    ElMessage.success($t('ui.actionMessage.deleteSuccess'));
    handleRefresh();
  } finally {
    loadingInstance.close();
  }
}

async function handleStatusChange(
  newStatus: number,
  row: SystemSmsTemplateApi.SmsTemplateRespVO,
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
        if (!row.id) {
          return reject(new Error('缺少编号'));
        }
        await updateSmsTemplateStatus(row.id, newStatus);
        ElMessage.success($t('ui.actionMessage.operationSuccess'));
        resolve(true);
      })
      .catch(() => reject(new Error('取消')));
  });
}

function handleRowCheckboxChange({
  records,
}: {
  records: SystemSmsTemplateApi.SmsTemplateRespVO[];
}) {
  checkedIds.value = records
    .map((item) => item.id)
    .filter((id): id is string => id !== undefined);
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
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          return await getSmsTemplatePage({
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
  } as VxeTableGridOptions<SystemSmsTemplateApi.SmsTemplateRespVO>,
});
</script>

<template>
  <Page auto-content-height>
    <SmsTemplateFormModal @success="handleRefresh" />
    <SmsTemplateSendFormModal @success="handleRefresh" />
    <ExportModal ref="exportTableRef" @success="handleExportSuccess" />

    <Grid table-title="短信模板">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.create', ['短信模板']),
              type: 'primary',
              icon: ACTION_ICON.ADD,
              auth: ['system:sms:template:create'],
              onClick: onCreate,
            },
            {
              label: $t('ui.actionTitle.export'),
              type: 'primary',
              icon: ACTION_ICON.DOWNLOAD,
              auth: ['system:sms:template:export'],
              onClick: onExport,
            },
            {
              label: $t('ui.actionTitle.deleteBatch'),
              type: 'danger',
              icon: ACTION_ICON.DELETE,
              disabled: isEmpty(checkedIds),
              auth: ['system:sms:template:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [
                  `${checkedIds.length}个短信模板`,
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
              label: '测试发送',
              type: 'text',
              icon: 'lucide:send',
              auth: ['system:sms:template:send-sms'],
              onClick: onSend.bind(null, row),
            },
            {
              label: $t('common.edit'),
              type: 'text',
              icon: ACTION_ICON.EDIT,
              auth: ['system:sms:template:update'],
              onClick: onEdit.bind(null, row),
            },
            {
              label: $t('common.delete'),
              type: 'text',
              danger: true,
              icon: ACTION_ICON.DELETE,
              auth: ['system:sms:template:delete'],
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
