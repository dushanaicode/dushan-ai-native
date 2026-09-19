<script lang="ts" setup>
import type { InfraMqApi } from '#/api/infra/mq';

import { ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { getMq } from '#/api/infra/mq';
import { useDescription } from '#/components';

import { useDetailSchema } from '../data';

defineOptions({ name: 'InfraMqDetail' });

const detail = ref<InfraMqApi.MqRespVO>();

const [Descriptions] = useDescription({
  componentProps: {
    bordered: true,
    column: 2,
    labelStyle: { width: '120px' },
    layout: 'horizontal',
    size: 'small',
  },
  data: detail,
  schema: useDetailSchema(),
});

const [Modal, modalApi] = useVbenModal({
  async onOpenChange(isOpen: boolean) {
    if (!isOpen) {
      detail.value = undefined;
      return;
    }

    const data = modalApi.getData() as undefined | { id: string };
    if (!data?.id) {
      return;
    }

    modalApi.lock();
    try {
      detail.value = await getMq(data.id);
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal
    class="w-1/2"
    title="消息定义详情"
    :show-cancel-button="false"
    :show-confirm-button="false"
  >
    <Descriptions :data="detail" class="mx-4" />
  </Modal>
</template>
