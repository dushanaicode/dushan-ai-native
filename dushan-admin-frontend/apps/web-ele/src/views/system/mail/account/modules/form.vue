<script lang="ts" setup>
import type { SystemMailAccountApi } from '#/api/system/mail/account';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  createMailAccount,
  getMailAccount,
  updateMailAccount,
} from '#/api/system/mail/account';
import { $t } from '#/locales';

import { useFormSchema } from '../data';

defineOptions({ name: 'SystemMailAccountForm' });

const emit = defineEmits(['success']);
const formData = ref<SystemMailAccountApi.MailAccountRespVO>();

const title = computed(() =>
  formData.value?.id
    ? $t('ui.actionTitle.edit', ['邮箱账号'])
    : $t('ui.actionTitle.create', ['邮箱账号']),
);

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    formItemClass: 'col-span-2',
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
      (await formApi.getValues()) as SystemMailAccountApi.MailAccountSaveReqVO;

    try {
      await (formData.value?.id
        ? updateMailAccount(data)
        : createMailAccount(data));
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
      | SystemMailAccountApi.MailAccountRespVO
      | undefined;
    if (!data?.id) {
      await formApi.setValues({
        password: '',
        sslEnable: true,
        starttlsEnable: false,
      });
      return;
    }

    modalApi.lock();
    try {
      formData.value = await getMailAccount(data.id);
      await formApi.setValues({
        ...formData.value,
        password: '',
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
