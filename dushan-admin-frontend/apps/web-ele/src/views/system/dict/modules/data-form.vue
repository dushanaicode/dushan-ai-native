<script lang="ts" setup>
import type { SystemDictDataApi } from '#/api/system/dict/data';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  createDictData,
  getDictData,
  updateDictData,
} from '#/api/system/dict/data';

import { useDataFormSchema } from '../data';

defineOptions({ name: 'SystemDictDataForm' });

const emit = defineEmits(['success']);
const formData = ref<SystemDictDataApi.DictDataRespVO>();

const title = computed(() =>
  formData.value?.id
    ? $t('ui.actionTitle.edit', ['字典数据'])
    : $t('ui.actionTitle.create', ['字典数据']),
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
  schema: useDataFormSchema(),
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
      (await formApi.getValues()) as SystemDictDataApi.DictDataSaveReqVO;

    try {
      await (formData.value?.id ? updateDictData(data) : createDictData(data));
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
      | SystemDictDataApi.DictDataRespVO
      | undefined
      | { dictType?: string };

    if (data && 'id' in data && data.id) {
      modalApi.lock();
      try {
        formData.value = await getDictData(data.id);
        await formApi.setValues(formData.value);
      } finally {
        modalApi.unlock();
      }
      return;
    }

    if (data && 'dictType' in data && data.dictType) {
      await formApi.setValues({
        dictType: data.dictType,
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
