<script lang="ts" setup>
import type { SystemSmsChannelApi } from '#/api/system/sms/channel';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  createSmsChannel,
  getSmsChannel,
  updateSmsChannel,
} from '#/api/system/sms/channel';
import { SwitchStatus } from '#/constants/status';
import { $t } from '#/locales';

import { useFormSchema } from '../data';

defineOptions({ name: 'SystemSmsChannelForm' });

const emit = defineEmits(['success']);
const formData = ref<SystemSmsChannelApi.SmsChannelRespVO>();

const getTitle = computed(() => {
  return formData.value?.id
    ? $t('ui.actionTitle.edit', ['短信渠道'])
    : $t('ui.actionTitle.create', ['短信渠道']);
});

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    formItemClass: 'col-span-1',
    labelWidth: 100,
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
      (await formApi.getValues()) as SystemSmsChannelApi.SmsChannelSaveReqVO;
    try {
      await (formData.value?.id
        ? updateSmsChannel(data)
        : createSmsChannel(data));
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
      | SystemSmsChannelApi.SmsChannelRespVO
      | undefined;
    if (!data?.id) {
      await formApi.setValues({ status: SwitchStatus.ENABLED });
      return;
    }

    modalApi.lock();
    try {
      formData.value = await getSmsChannel(data.id);
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
