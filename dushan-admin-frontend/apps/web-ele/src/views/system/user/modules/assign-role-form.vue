<script lang="ts" setup>
import type { SystemUserApi } from '#/api/system/user';

import { ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { assignUserRole, getUserRoleList } from '#/api/system/role';

import { useAssignRoleFormSchema } from '../data';

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
  schema: useAssignRoleFormSchema(),
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
        roleIds?: string[];
      };
      await assignUserRole(values.id, values.roleIds ?? []);
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

    modalApi.lock();
    try {
      const roleIds = await getUserRoleList(data.id);
      await formApi.setValues({
        id: data.id,
        nickname: data.nickname,
        roleIds,
        username: data.username,
      });
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal class="w-1/3" title="分配角色">
    <Form />
  </Modal>
</template>
