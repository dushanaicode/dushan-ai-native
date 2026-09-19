<script lang="ts" setup>
import type { SystemDictTypeApi } from '#/api/system/dict/type';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  createDictType,
  getDictType,
  updateDictType,
} from '#/api/system/dict/type';

import { useTypeFormSchema } from '../data';

defineOptions({ name: 'SystemDictTypeForm' });

const emit = defineEmits(['success']);
const formData = ref<SystemDictTypeApi.DictTypeRespVO>();

const title = computed(() =>
  formData.value?.id
    ? $t('ui.actionTitle.edit', ['字典类型'])
    : $t('ui.actionTitle.create', ['字典类型']),
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
  schema: useTypeFormSchema(),
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
      (await formApi.getValues()) as SystemDictTypeApi.DictTypeSaveReqVO;

    try {
      await (formData.value?.id ? updateDictType(data) : createDictType(data));
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
      | SystemDictTypeApi.DictTypeRespVO
      | undefined;
    if (!data?.id) {
      return;
    }

    modalApi.lock();
    try {
      formData.value = await getDictType(data.id);
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
