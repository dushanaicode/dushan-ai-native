<script lang="ts" setup>
import type { SystemTenantApi } from '#/api/system/tenant';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { createTenant, getTenant, updateTenant } from '#/api/system/tenant';
import { $t } from '#/locales';

import { useFormSchema } from '../data';

defineOptions({ name: 'SystemTenantForm' });

const emit = defineEmits(['success']);
const formData = ref<SystemTenantApi.TenantRespVO>();

const title = computed(() =>
  formData.value?.id
    ? $t('ui.actionTitle.edit', ['租户'])
    : $t('ui.actionTitle.create', ['租户']),
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
  schema: useFormSchema(),
  showDefaultActions: false,
});

function normalizeWebsites(websites?: string | string[]) {
  if (Array.isArray(websites)) {
    return websites.filter(Boolean);
  }

  return (websites ?? '')
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean);
}

function getFormValues(
  values: Record<string, any>,
): SystemTenantApi.TenantSaveReqVO | SystemTenantApi.TenantUpdateReqVO {
  const data = {
    accountCount: values.accountCount,
    contactMobile: values.contactMobile || undefined,
    contactName: values.contactName,
    expireTime: values.expireTime,
    id: values.id,
    name: values.name,
    packageId: values.packageId,
    status: values.status,
    websites: normalizeWebsites(values.websites),
  };

  if (formData.value?.id) {
    return data as SystemTenantApi.TenantUpdateReqVO;
  }

  return {
    ...data,
    password: values.password,
    username: values.username,
  } as SystemTenantApi.TenantSaveReqVO;
}

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid) {
      return;
    }

    modalApi.lock();
    const values = await formApi.getValues();
    const data = getFormValues(values);

    try {
      await (formData.value?.id
        ? updateTenant(data as SystemTenantApi.TenantUpdateReqVO)
        : createTenant(data as SystemTenantApi.TenantSaveReqVO));
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

    const data = modalApi.getData() as SystemTenantApi.TenantRespVO | undefined;
    if (!data?.id) {
      await formApi.setValues({
        websites: '',
      });
      return;
    }

    modalApi.lock();
    try {
      formData.value = await getTenant(data.id);
      await formApi.setValues({
        ...formData.value,
        websites: formData.value.websites?.join('\n') ?? '',
      });
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal class="w-1/2" :title="title">
    <Form class="mx-4" />
  </Modal>
</template>
