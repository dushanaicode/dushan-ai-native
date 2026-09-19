<script lang="ts" setup>
import type { SystemSmsTemplateApi } from '#/api/system/sms/template';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  createSmsTemplate,
  getSmsTemplate,
  updateSmsTemplate,
} from '#/api/system/sms/template';
import { SwitchStatus } from '#/constants/status';
import { $t } from '#/locales';

import { useFormSchema } from '../data';

defineOptions({ name: 'SystemSmsTemplateForm' });

const emit = defineEmits(['success']);
const formData = ref<SystemSmsTemplateApi.SmsTemplateRespVO>();

const getTitle = computed(() => {
  return formData.value?.id
    ? $t('ui.actionTitle.edit', ['短信模板'])
    : $t('ui.actionTitle.create', ['短信模板']);
});

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    formItemClass: 'col-span-1',
    labelWidth: 110,
  },
  layout: 'horizontal',
  schema: useFormSchema(),
  showDefaultActions: false,
});

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid) {
      return;
    }

    modalApi.lock();
    const data =
      (await formApi.getValues()) as SystemSmsTemplateApi.SmsTemplateSaveReqVO;
    try {
      await (formData.value?.id
        ? updateSmsTemplate(data)
        : createSmsTemplate(data));
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
      | SystemSmsTemplateApi.SmsTemplateRespVO
      | undefined;
    if (!data?.id) {
      await formApi.setValues({ status: SwitchStatus.ENABLED });
      return;
    }

    modalApi.lock();
    try {
      formData.value = await getSmsTemplate(data.id);
      await formApi.setValues(formData.value);
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal class="w-1/2" :title="getTitle">
    <Form class="mx-4" />
  </Modal>
</template>
