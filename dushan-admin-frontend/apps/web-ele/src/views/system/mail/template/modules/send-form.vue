<script lang="ts" setup>
import type { SystemMailTemplateApi } from '#/api/system/mail/template';

import { ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { getMailTemplate, sendMail } from '#/api/system/mail/template';

import { useSendMailFormSchema } from '../data';

defineOptions({ name: 'SystemMailTemplateSendForm' });

const emit = defineEmits(['success']);
const formData = ref<SystemMailTemplateApi.MailTemplateRespVO>();

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    formItemClass: 'col-span-2',
    labelWidth: 90,
  },
  layout: 'horizontal',
  showDefaultActions: false,
});

function parseEmails(text?: string): string[] {
  return (text ?? '')
    .split(/[\n,，]/)
    .map((email) => email.trim())
    .filter(Boolean);
}

function buildFormSchema(template?: SystemMailTemplateApi.MailTemplateRespVO) {
  const schema = useSendMailFormSchema();
  for (const param of template?.params ?? []) {
    schema.push({
      component: 'Input',
      componentProps: {
        placeholder: `请输入参数 ${param}`,
      },
      fieldName: `param_${param}`,
      label: `参数 ${param}`,
      rules: 'required',
    });
  }
  return schema;
}

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid) {
      return;
    }

    const values = await formApi.getValues();
    const toMails = parseEmails(values.toMails);
    if (toMails.length === 0) {
      ElMessage.error('请输入收件邮箱');
      return;
    }

    modalApi.lock();
    const templateParams: Record<string, any> = {};
    for (const param of formData.value?.params ?? []) {
      templateParams[param] = values[`param_${param}`];
    }

    try {
      await sendMail({
        bccMails: parseEmails(values.bccMails),
        ccMails: parseEmails(values.ccMails),
        templateCode: formData.value?.code ?? '',
        templateParams,
        toMails,
      });
      await modalApi.close();
      emit('success');
      ElMessage.success('邮件发送成功');
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
      return;
    }

    modalApi.lock();
    try {
      formData.value = await getMailTemplate(data.id);
      formApi.setState({ schema: buildFormSchema(formData.value) });
      await formApi.setValues({
        bccMails: '',
        ccMails: '',
        content: formData.value.content,
        toMails: '',
      });
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal class="w-1/2" title="测试发送邮件">
    <Form class="mx-4" />
  </Modal>
</template>
