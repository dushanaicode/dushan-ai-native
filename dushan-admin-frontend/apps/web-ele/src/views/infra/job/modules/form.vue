<script lang="ts" setup>
import type { InfraJobApi } from '#/api/infra/job';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { createJob, getJob, updateJob } from '#/api/infra/job';
import { $t } from '#/locales';

import { useFormSchema } from '../data';

defineOptions({ name: 'InfraJobForm' });

const emit = defineEmits<{
  success: [];
}>();

const formData = ref<InfraJobApi.JobRespVO>();

const title = computed(() =>
  formData.value?.id
    ? $t('ui.actionTitle.edit', ['任务'])
    : $t('ui.actionTitle.create', ['任务']),
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
      const values = await formApi.getValues();
      const data = normalizeJobValues(values);

      await (formData.value?.id ? updateJob(data) : createJob(data));
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

    const data = modalApi.getData() as InfraJobApi.JobRespVO | undefined;
    if (!data?.id) {
      await formApi.resetForm();
      await formApi.setValues({
        cronExpression: '* * * * *',
        retryCount: 0,
        retryInterval: 0,
      });
      return;
    }

    modalApi.lock();
    try {
      formData.value = await getJob(data.id);
      await formApi.setValues(formData.value);
    } finally {
      modalApi.unlock();
    }
  },
});

function normalizeJobValues(
  values: Record<string, unknown>,
): InfraJobApi.JobSaveReqVO {
  return {
    cronExpression: String(values.cronExpression ?? ''),
    handlerName: String(values.handlerName ?? ''),
    handlerParam:
      typeof values.handlerParam === 'string' && values.handlerParam
        ? values.handlerParam
        : undefined,
    id: toOptionalString(values.id),
    monitorTimeout: toOptionalNumber(values.monitorTimeout),
    name: String(values.name ?? ''),
    retryCount: Number(values.retryCount ?? 0),
    retryInterval: Number(values.retryInterval ?? 0),
  };
}

function toOptionalString(value: unknown) {
  if (typeof value !== 'string') {
    return undefined;
  }
  const trimmedValue = value.trim();
  return trimmedValue || undefined;
}

function toOptionalNumber(value: unknown) {
  if (value === undefined || value === null || value === '') {
    return undefined;
  }
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : undefined;
}
</script>

<template>
  <Modal :title="title" class="w-1/2">
    <Form class="mx-4" />
  </Modal>
</template>
