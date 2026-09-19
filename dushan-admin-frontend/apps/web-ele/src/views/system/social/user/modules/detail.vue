<script lang="ts" setup>
import type { SystemSocialUserApi } from '#/api/system/social/user';

import { ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { getSocialUser } from '#/api/system/social/user';
import { useDescription } from '#/components';

import { useDetailSchema } from '../data';

defineOptions({ name: 'SystemSocialUserDetail' });

const detail = ref<SystemSocialUserApi.SocialUserRespVO>();

const [Descriptions] = useDescription({
  componentProps: {
    bordered: true,
    column: 2,
    labelStyle: { width: '160px' },
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
      | SystemSocialUserApi.SocialUserRespVO
      | undefined;
    if (!data?.id) {
      return;
    }

    modalApi.lock();
    try {
      detail.value = await getSocialUser(data.id);
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal
    class="w-1/2"
    title="社交用户详情"
    :show-cancel-button="false"
    :show-confirm-button="false"
  >
    <Descriptions :data="detail" class="mx-4" />
  </Modal>
</template>
