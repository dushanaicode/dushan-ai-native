<script lang="ts" setup>
import type { SystemLoginLogApi } from '#/api/system/logger/loginlog';

import { ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { useDescription } from '#/components';

import { useDetailSchema } from '../data';

defineOptions({ name: 'SystemLoginLogDetail' });

const formData = ref<SystemLoginLogApi.LoginLogRespVO>();

const [Descriptions] = useDescription({
  componentProps: {
    bordered: true,
    column: 1,
    title: '',
  },
  data: formData,
  schema: useDetailSchema(),
});

const [Modal, modalApi] = useVbenModal({
  async onOpenChange(isOpen: boolean) {
    if (!isOpen) {
      formData.value = undefined;
      return;
    }

    const data = modalApi.getData() as
      | SystemLoginLogApi.LoginLogRespVO
      | undefined;
    if (!data?.id) {
      return;
    }

    modalApi.lock();
    try {
      formData.value = data;
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal
    class="w-1/2"
    title="登录日志详情"
    :show-cancel-button="false"
    :show-confirm-button="false"
  >
    <Descriptions :data="formData" />
  </Modal>
</template>
