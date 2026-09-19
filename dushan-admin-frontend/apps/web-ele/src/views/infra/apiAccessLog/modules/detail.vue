<script lang="ts" setup>
import type { InfraApiAccessLogApi } from '#/api/infra/api-access-log';

import { ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { useDescription } from '#/components';

import { useDetailSchema } from '../data';

defineOptions({ name: 'InfraApiAccessLogDetail' });

const detail = ref<InfraApiAccessLogApi.ApiAccessLogRespVO>();

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

    const data = modalApi.getData() as
      | InfraApiAccessLogApi.ApiAccessLogRespVO
      | undefined;
    if (!data?.id) {
      return;
    }

    detail.value = data;
  },
});
</script>

<template>
  <Modal
    class="w-1/2"
    title="API 访问日志详情"
    :show-cancel-button="false"
    :show-confirm-button="false"
  >
    <Descriptions :data="detail" class="mx-4" />
  </Modal>
</template>
