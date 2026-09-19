<script lang="ts" setup>
import type { SystemMailTemplateApi } from '#/api/system/mail/template';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  createMailTemplate,
  getMailTemplate,
  updateMailTemplate,
} from '#/api/system/mail/template';
import { $t } from '#/locales';

import { useFormSchema } from '../data';

defineOptions({ name: 'SystemMailTemplateForm' });

const emit = defineEmits(['success']);
const formData = ref<SystemMailTemplateApi.MailTemplateRespVO>();

const title = computed(() =>
  formData.value?.id
    ? $t('ui.actionTitle.edit', ['邮件模板'])
    : $t('ui.actionTitle.create', ['邮件模板']),
);

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    formItemClass: 'col-span-2',
    labelWidth: 100,
  },
  layout: 'horizontal',
  schema: useFormSchema(),
  showDefaultActions: false,
});

function normalizeParams(params?: string | string[]) {
  if (Array.isArray(params)) {
    return params.filter(Boolean);
  }

  return (params ?? '')
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean);
}

function getFormValues(
  values: Record<string, any>,
): SystemMailTemplateApi.MailTemplateSaveReqVO {
  return {
    accountId: values.accountId,
    code: values.code,
    content: values.content,
    id: values.id,
    name: values.name,
    nickname: values.nickname,
    params: normalizeParams(values.params),
    remark: values.remark || undefined,
    status: values.status,
    title: values.title,
  };
}

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid) {
      return;
    }

    modalApi.lock();
    const values = await formApi.getValues();
    const data = getFormValues(values);

    try {
      await (formData.value?.id
        ? updateMailTemplate(data)
        : createMailTemplate(data));
      await modalApi.close();
      emit('success');
      ElMessage.success($t('ui.actionMessage.operationSuccess'));
    } finally {
      modalApi.unlock();
    }
  },
  async onOpenChange(isOpen: boolean) {
    if (!isOpen) {
      formData.value = undefined;
      return;
    }

    const data = modalApi.getData() as
      | SystemMailTemplateApi.MailTemplateRespVO
      | undefined;
    if (!data?.id) {
      await formApi.setValues({
        params: '',
      });
      return;
    }

    modalApi.lock();
    try {
      formData.value = await getMailTemplate(data.id);
      await formApi.setValues({
        ...formData.value,
        params: formData.value.params?.join('\n') ?? '',
      });
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal class="w-1/2" :title="title">
    <Form class="mx-4" />
  </Modal>
</template>
