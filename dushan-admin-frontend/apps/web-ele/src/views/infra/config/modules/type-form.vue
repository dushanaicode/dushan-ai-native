<script lang="ts" setup>
import type { InfraConfigTypeApi } from '#/api/infra/config/type';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  createConfigType,
  getConfigType,
  updateConfigType,
} from '#/api/infra/config/type';
import { SwitchStatus } from '#/constants/status';
import { $t } from '#/locales';

import { useTypeFormSchema } from '../data';

defineOptions({ name: 'InfraConfigTypeForm' });

const emit = defineEmits<{
  success: [];
}>();

const formData = ref<InfraConfigTypeApi.ConfigTypeRespVO>();

const title = computed(() =>
  formData.value?.id
    ? $t('ui.actionTitle.edit', ['配置类型'])
    : $t('ui.actionTitle.create', ['配置类型']),
);

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    formItemClass: 'col-span-2',
    labelWidth: 90,
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
    try {
      const values =
        (await formApi.getValues()) as InfraConfigTypeApi.ConfigTypeSaveReqVO;
      const data = normalizeTypeValues(values);
      await (formData.value?.id
        ? updateConfigType(data)
        : createConfigType(data));
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
      await formApi.resetForm();
      return;
    }

    const data = modalApi.getData() as
      | InfraConfigTypeApi.ConfigTypeRespVO
      | undefined;
    if (!data?.id) {
      await formApi.resetForm();
      await formApi.setValues({
        module: 'system',
        status: SwitchStatus.ENABLED,
      });
      return;
    }

    modalApi.lock();
    try {
      formData.value = await getConfigType(data.id);
      await formApi.setValues(formData.value);
    } finally {
      modalApi.unlock();
    }
  },
});

function emptyToUndefined(value?: null | string) {
  return value === '' || value === null ? undefined : value;
}

function normalizeTypeValues(
  values: InfraConfigTypeApi.ConfigTypeSaveReqVO,
): InfraConfigTypeApi.ConfigTypeSaveReqVO {
  return {
    code: values.code,
    id: values.id,
    module: values.module || 'system',
    name: values.name,
    remark: emptyToUndefined(values.remark),
    status: Number(values.status),
  };
}
</script>

<template>
  <Modal :title="title" class="w-1/3">
    <Form class="mx-4" />
  </Modal>
</template>
