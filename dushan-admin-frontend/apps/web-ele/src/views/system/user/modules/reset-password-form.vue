<script lang="ts" setup>
import type { SystemUserApi } from '#/api/system/user';

import { ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { updateUserPassword } from '#/api/system/user';

import { useResetPasswordFormSchema } from '../data';

const emit = defineEmits<{
  success: [];
}>();

const formData = ref<null | SystemUserApi.UserRespVO>(null);

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
  },
  layout: 'horizontal',
  schema: useResetPasswordFormSchema(),
  showDefaultActions: false,
});

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid) return;

    modalApi.lock();
    try {
      const values = (await formApi.getValues()) as {
        id: string;
        password: string;
      };
      await updateUserPassword(values.id, values.password);
      ElMessage.success($t('ui.actionMessage.operationSuccess'));
      emit('success');
      modalApi.close();
    } finally {
      modalApi.unlock();
    }
  },
  async onOpenChange(isOpen) {
    if (!isOpen) {
      formData.value = null;
      return;
    }

    const data = modalApi.getData() as SystemUserApi.UserRespVO;
    formData.value = data;
    await formApi.setValues({
      id: data.id,
      password: '',
      username: data.username,
    });
  },
});
</script>

<template>
  <Modal class="w-1/3" title="重置密码">
    <Form />
  </Modal>
</template>
