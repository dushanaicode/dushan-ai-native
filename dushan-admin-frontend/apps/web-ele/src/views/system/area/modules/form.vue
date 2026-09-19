<script lang="ts" setup>
import { useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { getAreaByIp } from '#/api/system/area';

import { useFormSchema } from '../data';

defineOptions({ name: 'SystemAreaIpQueryForm' });

const [Form, formApi] = useVbenForm({
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
    const data = await formApi.getValues();

    try {
      const result = await getAreaByIp(data.ip);
      await formApi.setFieldValue('result', result);
      ElMessage.success($t('ui.actionMessage.operationSuccess'));
    } finally {
      modalApi.unlock();
    }
  },
  async onOpenChange(isOpen: boolean) {
    if (!isOpen) {
      await formApi.resetForm();
    }
  },
});
</script>

<template>
  <Modal class="w-1/3" title="IP 查询">
    <Form class="mx-4" />
  </Modal>
</template>
