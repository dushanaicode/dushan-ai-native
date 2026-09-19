<script lang="ts" setup>
import type { InfraApiErrorLogApi } from '#/api/infra/api-error-log';

import { ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { useDescription } from '#/components';

import { useDetailSchema } from '../data';

defineOptions({ name: 'InfraApiErrorLogDetail' });

const detail = ref<InfraApiErrorLogApi.ApiErrorLogRespVO>();

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
      | InfraApiErrorLogApi.ApiErrorLogRespVO
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
    title="API 错误日志详情"
    :show-cancel-button="false"
    :show-confirm-button="false"
  >
    <Descriptions :data="detail" class="mx-4" />
  </Modal>
</template>
