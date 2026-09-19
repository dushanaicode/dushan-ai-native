<script lang="ts" setup>
import type { InfraDataSourceConfigApi } from '#/api/infra/data-source-config';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  createDataSourceConfig,
  getDataSourceConfig,
  updateDataSourceConfig,
} from '#/api/infra/data-source-config';
import { SwitchStatus } from '#/constants/status';
import { $t } from '#/locales';

import { useFormSchema } from '../data';

defineOptions({ name: 'InfraDataSourceConfigForm' });

const emit = defineEmits<{
  success: [];
}>();

const formData = ref<InfraDataSourceConfigApi.DataSourceConfigRespVO>();

const title = computed(() =>
  formData.value?.id
    ? $t('ui.actionTitle.edit', ['数据源'])
    : $t('ui.actionTitle.create', ['数据源']),
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
      const values = (await formApi.getValues()) as Record<string, unknown>;
      const data = normalizeDataSourceValues(values);
      if (!data) {
        return;
      }

      await (formData.value?.id
        ? updateDataSourceConfig(data)
        : createDataSourceConfig(data));
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
      | InfraDataSourceConfigApi.DataSourceConfigRespVO
      | undefined;
    if (!data?.id) {
      await formApi.resetForm();
      await formApi.setValues({
        echo: false,
        isDefault: false,
        maxOverflow: 20,
        poolRecycle: 3600,
        poolSize: 10,
        poolTimeout: 30,
        sourceType: 1,
        status: SwitchStatus.ENABLED,
      });
      return;
    }

    modalApi.lock();
    try {
      formData.value = await getDataSourceConfig(data.id);
      await formApi.setValues(formData.value);
    } finally {
      modalApi.unlock();
    }
  },
});

function normalizeDataSourceValues(
  values: Record<string, unknown>,
): InfraDataSourceConfigApi.DataSourceConfigSaveReqVO | undefined {
  const url = normalizeUrl(values.url);
  if (!url) {
    ElMessage.error('请输入数据源连接 URL');
    return undefined;
  }

  const status = Number(values.status);
  const isDefault = toBoolean(values.isDefault);

  if (formData.value?.isDefault && !isDefault) {
    ElMessage.warning('默认数据源不能取消默认');
    return undefined;
  }

  if (formData.value?.isDefault && status === SwitchStatus.DISABLED) {
    ElMessage.warning('默认数据源不能禁用');
    return undefined;
  }

  if (isDefault && status !== SwitchStatus.ENABLED) {
    ElMessage.warning('只能将启用状态的数据源设为默认');
    return undefined;
  }

  return {
    dbType: inferDbType(url, formData.value?.dbType),
    echo: toBoolean(values.echo),
    id: toOptionalString(values.id),
    isDefault,
    maxOverflow: Number(values.maxOverflow),
    name: String(values.name ?? '').trim(),
    poolRecycle: Number(values.poolRecycle),
    poolSize: Number(values.poolSize),
    poolTimeout: Number(values.poolTimeout),
    remark: toOptionalString(values.remark),
    sourceType: Number(values.sourceType),
    status,
    url,
  };
}

function normalizeUrl(url: unknown) {
  return typeof url === 'string' ? url.trim() : '';
}

function toBoolean(value: unknown) {
  if (typeof value === 'boolean') {
    return value;
  }
  if (value === 'true') {
    return true;
  }
  if (value === 'false') {
    return false;
  }
  return Boolean(value);
}

function toOptionalString(value: unknown) {
  if (typeof value !== 'string') {
    return undefined;
  }
  const trimmedValue = value.trim();
  return trimmedValue || undefined;
}

function inferDbType(url: unknown, fallback = 'mysql') {
  if (typeof url !== 'string') {
    return fallback;
  }

  const protocol = url.toLowerCase().split(':')[0] || fallback;
  return protocol.split('+')[0] || fallback;
}
</script>

<template>
  <Modal :title="title" class="w-1/2">
    <Form class="mx-4" />
  </Modal>
</template>
