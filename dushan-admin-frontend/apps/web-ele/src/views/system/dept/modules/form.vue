<script lang="ts" setup>
import type { SystemDeptApi } from '#/api/system/dept';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { createDept, getDept, updateDept } from '#/api/system/dept';

import { useFormSchema } from '../data';

defineOptions({ name: 'SystemDeptForm' });

const emit = defineEmits(['success']);
const formData = ref<SystemDeptApi.DeptRespVO>();

const title = computed(() =>
  formData.value?.id
    ? $t('ui.actionTitle.edit', ['部门'])
    : $t('ui.actionTitle.create', ['部门']),
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
    const data = (await formApi.getValues()) as SystemDeptApi.DeptSaveReqVO;

    try {
      await (formData.value?.id ? updateDept(data) : createDept(data));
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
      | SystemDeptApi.DeptRespVO
      | undefined
      | { parentId?: string };

    if (data && 'id' in data && data.id) {
      modalApi.lock();
      try {
        formData.value = await getDept(data.id);
        await formApi.setValues(formData.value);
      } finally {
        modalApi.unlock();
      }
      return;
    }

    if (data && 'parentId' in data) {
      await formApi.setValues({
        parentId: data.parentId,
      });
    }
  },
});
</script>

<template>
  <Modal :title="title">
    <Form class="mx-4" />
  </Modal>
</template>
