<script lang="ts" setup>
import type { InfraFileConfigApi } from '#/api/infra/file-config';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  createFileConfig,
  getFileConfig,
  updateFileConfig,
} from '#/api/infra/file-config';
import { $t } from '#/locales';

import { useFormSchema } from '../data';

defineOptions({ name: 'InfraFileConfigForm' });

const emit = defineEmits<{
  success: [];
}>();

const formData = ref<InfraFileConfigApi.FileConfigRespVO>();

const title = computed(() =>
  formData.value?.id
    ? $t('ui.actionTitle.edit', ['文件配置'])
    : $t('ui.actionTitle.create', ['文件配置']),
);

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    formItemClass: 'col-span-2',
    labelWidth: 130,
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
      const values = (await formApi.getValues()) as Record<string, unknown>;
      const data = normalizeFileConfigValues(values);
      await (formData.value?.id
        ? updateFileConfig(data)
        : createFileConfig(data));
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
      | InfraFileConfigApi.FileConfigRespVO
      | undefined;
    if (!data?.id) {
      await formApi.resetForm();
      return;
    }

    modalApi.lock();
    try {
      formData.value = await getFileConfig(data.id);
      await formApi.setValues(formData.value);
    } finally {
      modalApi.unlock();
    }
  },
});

function pickConfig(config: Record<string, unknown>, keys: string[]) {
  const result: Record<string, unknown> = {};
  for (const key of keys) {
    const value = config[key];
    if (value !== undefined && value !== null && value !== '') {
      result[key] = value;
    }
  }
  return result;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function toOptionalString(value: unknown) {
  if (typeof value !== 'string') {
    return undefined;
  }
  const trimmedValue = value.trim();
  return trimmedValue || undefined;
}

function normalizeFileConfigValues(
  values: Record<string, unknown>,
): InfraFileConfigApi.FileConfigSaveReqVO {
  const storage = Number(values.storage);
  const config = isRecord(values.config) ? values.config : {};
  const configKeysMap: Record<number, string[]> = {
    1: ['domain'],
    10: ['basePath', 'domain'],
    11: ['basePath', 'domain', 'host', 'port', 'username', 'password', 'mode'],
    12: [
      'basePath',
      'domain',
      'host',
      'port',
      'username',
      'password',
      'knownHosts',
    ],
    20: [
      'endpoint',
      'bucket',
      'accessKey',
      'accessSecret',
      'region',
      'domain',
      'enablePathStyleAccess',
    ],
  };

  return {
    config: pickConfig(config, configKeysMap[storage] || []),
    id: toOptionalString(values.id),
    name: String(values.name ?? ''),
    remark: toOptionalString(values.remark),
    storage,
  };
}
</script>

<template>
  <Modal :title="title" class="w-1/2">
    <Form class="mx-4" />
  </Modal>
</template>
