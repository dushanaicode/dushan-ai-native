<script lang="ts" setup>
import type { VbenFormSchema } from '#/adapter/form';
import type { SystemSmsTemplateApi } from '#/api/system/sms/template';

import { ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { getSmsTemplate, sendSms } from '#/api/system/sms/template';

import { useSendSmsFormSchema } from '../data';

defineOptions({ name: 'SystemSmsTemplateSendForm' });

const emit = defineEmits(['success']);
const formData = ref<SystemSmsTemplateApi.SmsTemplateRespVO>();

function buildFormSchema(params?: string[]): VbenFormSchema[] {
  const schema = useSendSmsFormSchema();
  params?.forEach((param) => {
    schema.push({
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: `请输入 ${param}`,
      },
      fieldName: `param_${param}`,
      formItemClass: 'col-span-2',
      label: param,
      rules: 'required',
    });
  });
  return schema;
}

function collectTemplateParams(values: Record<string, any>) {
  const params: Record<string, any> = {};
  for (const param of formData.value?.params || []) {
    params[param] = values[`param_${param}`];
  }
  return params;
}

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    formItemClass: 'col-span-1',
    labelWidth: 100,
  },
  layout: 'horizontal',
  showDefaultActions: false,
});

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid || !formData.value?.code) {
      return;
    }

    modalApi.lock();
    const values = await formApi.getValues();
    try {
      await sendSms({
        mobile: values.mobile,
        templateCode: formData.value.code,
        templateParams: collectTemplateParams(values),
      });
      await modalApi.close();
      emit('success');
      ElMessage.success('短信发送成功');
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
      | SystemSmsTemplateApi.SmsTemplateRespVO
      | undefined;
    if (!data?.id) {
      return;
    }

    modalApi.lock();
    try {
      formData.value = await getSmsTemplate(data.id);
      await formApi.setState({
        schema: buildFormSchema(formData.value.params),
      });
      await formApi.setValues({
        content: formData.value.content,
      });
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal class="w-1/2" title="发送测试短信">
    <Form class="mx-4" />
  </Modal>
</template>
