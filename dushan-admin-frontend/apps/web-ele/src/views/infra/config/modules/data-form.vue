<script lang="ts" setup>
import type { InfraConfigDataApi } from '#/api/infra/config/data';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  createConfigData,
  getConfigData,
  updateConfigData,
} from '#/api/infra/config/data';
import { $t } from '#/locales';

import { useDataFormSchema } from '../data';

defineOptions({ name: 'InfraConfigDataForm' });

const emit = defineEmits<{
  success: [];
}>();

interface ConfigDataFormModalData extends Partial<InfraConfigDataApi.ConfigDataRespVO> {
  lockTypeId?: boolean;
}

const formData = ref<InfraConfigDataApi.ConfigDataRespVO>();

const title = computed(() =>
  formData.value?.id
    ? $t('ui.actionTitle.edit', ['配置数据'])
    : $t('ui.actionTitle.create', ['配置数据']),
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
    try {
      const values = (await formApi.getValues()) as Record<string, unknown>;
      const data = normalizeDataValues(values);
      if (!data) {
        return;
      }
      await (formData.value?.id
        ? updateConfigData(data)
        : createConfigData(data));
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

    const data = modalApi.getData() as ConfigDataFormModalData | undefined;

    if (data && 'id' in data && data.id) {
      modalApi.lock();
      try {
        formData.value = await getConfigData(data.id);
        await formApi.setValues({
          ...formData.value,
          lockTypeId: false,
        });
      } finally {
        modalApi.unlock();
      }
      return;
    }

    await formApi.resetForm();
    await formApi.setValues({
      lockTypeId: Boolean(data?.lockTypeId),
      sort: 0,
      typeId: data?.typeId,
      visible: true,
    });
  },
});

function emptyToUndefined(value?: null | string) {
  return value === '' || value === null ? undefined : value;
}

function normalizeInputProps(
  value: unknown,
): { valid: false } | { valid: true; value?: string } {
  if (typeof value !== 'string') {
    return { valid: true };
  }

  const inputProps = value.trim();
  if (!inputProps) {
    return { valid: true };
  }

  try {
    JSON.parse(inputProps);
    return { valid: true, value: inputProps };
  } catch {
    ElMessage.error('控件属性必须是合法 JSON');
    return { valid: false };
  }
}

function normalizeDataValues(
  values: Record<string, unknown>,
): InfraConfigDataApi.ConfigDataSaveReqVO | undefined {
  const typeId = asOptionalString(values.typeId);
  if (!typeId) {
    ElMessage.error('请选择配置类型');
    return undefined;
  }

  const inputProps = normalizeInputProps(values.inputProps);
  if (!inputProps.valid) {
    return undefined;
  }

  return {
    description: emptyToUndefined(asOptionalString(values.description)),
    id: asOptionalString(values.id),
    inputProps: inputProps.value,
    inputType: emptyToUndefined(asOptionalString(values.inputType)),
    key: String(values.key ?? ''),
    name: String(values.name ?? ''),
    remark: emptyToUndefined(asOptionalString(values.remark)),
    sort: Number(values.sort ?? 0),
    typeId,
    value: String(values.value ?? ''),
    visible: toBoolean(values.visible),
  };
}

function asOptionalString(value: unknown) {
  return typeof value === 'string' ? value : undefined;
}

function toBoolean(value: unknown) {
  if (typeof value === 'boolean') {
    return value;
  }
  if (typeof value === 'string') {
    return value === 'true';
  }
  return value === undefined ? true : Boolean(value);
}
</script>

<template>
  <Modal :title="title" class="w-1/2">
    <Form class="mx-4" />
  </Modal>
</template>
