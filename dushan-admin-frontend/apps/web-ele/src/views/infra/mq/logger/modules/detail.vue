<script lang="ts" setup>
import type { InfraMqLogApi } from '#/api/infra/mq/log';

import { ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { getMqLog } from '#/api/infra/mq/log';
import { useDescription } from '#/components';

import { useDetailSchema } from '../data';

defineOptions({ name: 'InfraMqLogDetail' });

const detail = ref<InfraMqLogApi.MqLogRespVO>();

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
      detail.value = await getMqLog(data.id);
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal
    class="w-1/2"
    title="消费日志详情"
    :show-cancel-button="false"
    :show-confirm-button="false"
  >
    <Descriptions :data="detail" class="mx-4" />
  </Modal>
</template>
