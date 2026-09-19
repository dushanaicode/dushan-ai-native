<script lang="ts" setup>
import type { InfraJobLogApi } from '#/api/infra/job/log';

import { ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { getJobLog } from '#/api/infra/job/log';
import { useDescription } from '#/components';

import { useDetailSchema } from '../data';

defineOptions({ name: 'InfraJobLogDetail' });

const detail = ref<InfraJobLogApi.JobLogRespVO>();

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
      detail.value = await getJobLog(data.id);
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal
    class="w-1/2"
    title="日志详情"
    :show-cancel-button="false"
    :show-confirm-button="false"
  >
    <Descriptions :data="detail" class="mx-4" />
  </Modal>
</template>
