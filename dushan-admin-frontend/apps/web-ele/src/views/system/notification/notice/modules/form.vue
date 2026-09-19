<script lang="ts" setup>
import type { SystemNoticeApi } from '#/api/system/notification/notice';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  createNotice,
  getNotice,
  updateNotice,
} from '#/api/system/notification/notice';
import { $t } from '#/locales';

import { useFormSchema } from '../data';

defineOptions({ name: 'SystemNoticeForm' });

const emit = defineEmits(['success']);
const formData = ref<SystemNoticeApi.NoticeRespVO>();

const title = computed(() =>
  formData.value?.id
    ? $t('ui.actionTitle.edit', ['通知'])
    : $t('ui.actionTitle.create', ['通知']),
);

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    formItemClass: 'col-span-1',
    labelWidth: 90,
  },
  layout: 'horizontal',
  schema: useFormSchema(),
  showDefaultActions: false,
  wrapperClass: 'grid-cols-2',
});

function normalizeSaveData(
  values: Record<string, any>,
): SystemNoticeApi.NoticeSaveReqVO {
  const channels = Array.isArray(values.channels) ? values.channels : [];
  return {
    ...values,
    channels,
    mailAccountId: channels.includes('MAIL') ? values.mailAccountId : undefined,
    smsTemplateCode: channels.includes('SMS')
      ? values.smsTemplateCode
      : undefined,
  } as SystemNoticeApi.NoticeSaveReqVO;
}

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid) {
      return;
    }

    modalApi.lock();
    const values = await formApi.getValues();
    const data = normalizeSaveData(values);

    try {
      await (formData.value?.id ? updateNotice(data) : createNotice(data));
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

    const data = modalApi.getData() as SystemNoticeApi.NoticeRespVO | undefined;
    if (!data?.id) {
      return;
    }

    modalApi.lock();
    try {
      formData.value = await getNotice(data.id);
      await formApi.setValues(formData.value);
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal class="w-[760px]" :title="title">
    <Form class="mx-4" />
  </Modal>
</template>
