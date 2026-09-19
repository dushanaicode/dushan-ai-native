<script lang="ts" setup>
import type { SystemRoleApi } from '#/api/system/role';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { createRole, getRole, updateRole } from '#/api/system/role';

import { useFormSchema } from '../data';

defineOptions({ name: 'SystemRoleForm' });

const emit = defineEmits<{
  success: [];
}>();

const formData = ref<SystemRoleApi.RoleRespVO>();

const title = computed(() =>
  formData.value?.id
    ? $t('ui.actionTitle.edit', ['角色'])
    : $t('ui.actionTitle.create', ['角色']),
);

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    formItemClass: 'col-span-2',
    labelWidth: 80,
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
    const data = (await formApi.getValues()) as SystemRoleApi.RoleSaveReqVO;

    try {
      await (formData.value?.id ? updateRole(data) : createRole(data));
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

    const data = modalApi.getData() as SystemRoleApi.RoleRespVO | undefined;
    if (!data?.id) {
      return;
    }

    modalApi.lock();
    try {
      formData.value = await getRole(data.id);
      await formApi.setValues(formData.value);
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal :title="title">
    <Form class="mx-4" />
  </Modal>
</template>
