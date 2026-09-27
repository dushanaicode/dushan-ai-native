<script lang="ts" setup>
import type { InfraMqApi } from '#/api/infra/mq';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  createMq,
  getMq,
  getRegisteredConsumers,
  updateMq,
} from '#/api/infra/mq';
import { $t } from '#/locales';

import { useFormSchema } from '../data';

defineOptions({ name: 'InfraMqForm' });

const emit = defineEmits<{
  success: [];
}>();

const formData = ref<InfraMqApi.MqRespVO>();
const consumers = ref<InfraMqApi.ConsumerDeclaration[]>([]);

const title = computed(() =>
  formData.value?.id
    ? $t('ui.actionTitle.edit', ['消息定义'])
    : $t('ui.actionTitle.create', ['消息定义']),
);

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
    try {
      const data = await formApi.getValues<InfraMqApi.MqSaveReqVO>();

      await (formData.value?.id ? updateMq(data) : createMq(data));
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
      await formApi.reset();
      return;
    }

    modalApi.lock();
    try {
      await formApi.reset();
      consumers.value = await getRegisteredConsumers();
      formApi.updateSchema([
        {
          fieldName: 'consumer',
          componentProps: {
            options: consumers.value.map((item) => ({
              label: item.key,
              value: item.key,
            })),
            onChange: (key: string) => {
              const selected = consumers.value.find((item) => item.key === key);
              if (selected) {
                formApi.setFieldValue('topic', selected.topic);
                formApi.setFieldValue('retryCount', selected.retryCount);
              }
            },
          },
        },
      ]);
      const data = modalApi.getData() as InfraMqApi.MqRespVO | undefined;
      if (!data?.id) return;
      formData.value = await getMq(data.id);
      await formApi.setValues(formData.value);
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal :title="title" class="w-1/2">
    <Form class="mx-4" />
  </Modal>
</template>
