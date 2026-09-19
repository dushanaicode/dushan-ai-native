<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemMailAccountApi } from '#/api/system/mail/account';
import type { SystemMailTemplateApi } from '#/api/system/mail/template';

import { onMounted, ref } from 'vue';

import { confirm, Page, useVbenModal } from '@vben/common-ui';
import { isEmpty } from '@vben/utils';

import { ElLoading, ElMessage } from 'element-plus';

import { ACTION_ICON, TableAction, useVbenVxeGrid } from '#/adapter/vxe-table';
import { getSimpleMailAccountList } from '#/api/system/mail/account';
import {
  deleteMailTemplate,
  deleteMailTemplateList,
  exportMailTemplate,
  getExportMailTemplateFields,
  getMailTemplatePage,
  updateMailTemplateStatus,
} from '#/api/system/mail/template';
import { useExportModal } from '#/components';
import { DICT_TYPE } from '#/constants/dict-types';
import { $t } from '#/locales';
import { useDictionary } from '#/services/dictionary/context';

import { useGridColumns, useGridFormSchema } from './data';
import MailTemplateForm from './modules/form.vue';
import MailTemplateSendForm from './modules/send-form.vue';

defineOptions({ name: 'SystemMailTemplate' });

const dictionary = useDictionary();

const [MailTemplateFormModal, mailTemplateFormModalApi] = useVbenModal({
  connectedComponent: MailTemplateForm,
  destroyOnClose: true,
});

const [MailTemplateSendFormModal, mailTemplateSendFormModalApi] = useVbenModal({
  connectedComponent: MailTemplateSendForm,
  destroyOnClose: true,
});

const { ExportModal } = useExportModal();
const exportTableRef = ref();
const checkedIds = ref<string[]>([]);
const mailAccounts = ref<SystemMailAccountApi.MailAccountSimpleRespVO[]>([]);

function handleRefresh() {
  gridApi.query();
}

function getAccountMail(accountId: string) {
  return mailAccounts.value.find((item) => item.id === accountId)?.mail;
}

async function loadMailAccounts() {
  mailAccounts.value = await getSimpleMailAccountList();
}

async function onExport() {
  const fields = await getExportMailTemplateFields();
  const formValues = await gridApi.formApi.getValues();

  exportTableRef.value?.setData({
    columns: fields,
    exportApi: exportMailTemplate,
    fileName: '邮件模板数据.xls',
    searchParams: formValues,
  });
  exportTableRef.value?.open();
}

function handleExportSuccess() {
  ElMessage.success($t('ui.actionMessage.operationSuccess'));
}

function onCreate() {
  mailTemplateFormModalApi.setData(null).open();
}

function onEdit(row: SystemMailTemplateApi.MailTemplateRespVO) {
  mailTemplateFormModalApi.setData(row).open();
}

function onSend(row: SystemMailTemplateApi.MailTemplateRespVO) {
  mailTemplateSendFormModalApi.setData(row).open();
}

async function onDelete(row: SystemMailTemplateApi.MailTemplateRespVO) {
  const loadingInstance = ElLoading.service({
    fullscreen: true,
    text: $t('ui.actionMessage.deleting', [row.name]),
  });

  try {
    await deleteMailTemplate(row.id);
    ElMessage.success($t('ui.actionMessage.deleteSuccess', [row.name]));
    handleRefresh();
  } finally {
    loadingInstance.close();
  }
}

async function handleStatusChange(
  newStatus: number,
  row: SystemMailTemplateApi.MailTemplateRespVO,
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
        await updateMailTemplateStatus(row.id, newStatus);
        ElMessage.success($t('ui.actionMessage.operationSuccess'));
        resolve(true);
      })
      .catch(() => reject(new Error('取消')));
  });
}

async function onDeleteBatch() {
  await deleteMailTemplateList(checkedIds.value);
  checkedIds.value = [];
  ElMessage.success($t('ui.actionMessage.deleteSuccess'));
  handleRefresh();
}

function handleRowCheckboxChange({
  records,
}: {
  records: SystemMailTemplateApi.MailTemplateRespVO[];
}) {
  checkedIds.value = records.map((item) => item.id);
}

onMounted(() => {
  void loadMailAccounts();
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
    columns: useGridColumns(getAccountMail, handleStatusChange),
    height: 'auto',
    keepSource: true,
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          return await getMailTemplatePage({
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
  } as VxeTableGridOptions<SystemMailTemplateApi.MailTemplateRespVO>,
});
</script>

<template>
  <Page auto-content-height>
    <MailTemplateFormModal @success="handleRefresh" />
    <MailTemplateSendFormModal @success="handleRefresh" />
    <ExportModal ref="exportTableRef" @success="handleExportSuccess" />

    <Grid table-title="邮件模板">
      <template #toolbar-tools>
        <TableAction
          :actions="[
            {
              label: $t('ui.actionTitle.create', ['邮件模板']),
              type: 'primary',
              icon: ACTION_ICON.ADD,
              auth: ['system:mail:template:create'],
              onClick: onCreate,
            },
            {
              label: $t('ui.actionTitle.export'),
              type: 'primary',
              icon: ACTION_ICON.DOWNLOAD,
              auth: ['system:mail:template:export'],
              onClick: onExport,
            },
            {
              label: $t('ui.actionTitle.deleteBatch'),
              type: 'danger',
              icon: ACTION_ICON.DELETE,
              disabled: isEmpty(checkedIds),
              auth: ['system:mail:template:delete'],
              popConfirm: {
                title: $t('ui.actionMessage.deleteConfirm', [
                  `${checkedIds.length}个邮件模板`,
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
              auth: ['system:mail:template:send-mail'],
              onClick: onSend.bind(null, row),
            },
            {
              label: $t('common.edit'),
              type: 'text',
              icon: ACTION_ICON.EDIT,
              auth: ['system:mail:template:update'],
              onClick: onEdit.bind(null, row),
            },
            {
              label: $t('common.delete'),
              type: 'text',
              danger: true,
              icon: ACTION_ICON.DELETE,
              auth: ['system:mail:template:delete'],
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
