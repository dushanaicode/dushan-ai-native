<script lang="ts" setup>
import type { InfraJobApi } from '#/api/infra/job';

import { ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { getJob, getJobNextTimes } from '#/api/infra/job';
import { useDescription } from '#/components';

import { useDetailSchema } from '../data';

defineOptions({ name: 'InfraJobDetail' });

type JobDetail = InfraJobApi.JobRespVO & {
  nextTimes?: string[];
};

const detail = ref<JobDetail>();

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
      const [job, nextTimes] = await Promise.all([
        getJob(data.id),
        getJobNextTimes(data.id),
      ]);
      detail.value = { ...job, nextTimes };
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal
    class="w-1/2"
    title="任务详情"
    :show-cancel-button="false"
    :show-confirm-button="false"
  >
    <Descriptions :data="detail" class="mx-4" />
  </Modal>
</template>
