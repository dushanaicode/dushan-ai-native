<script lang="ts" setup>
import type { SystemAnnouncementApi } from '#/api/system/announcement';

import { ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { VbenTiptapPreview } from '@vben/plugins/tiptap';
import { formatDateTime } from '@vben/utils';

import { ElDescriptions, ElDescriptionsItem } from 'element-plus';

import { getAnnouncement } from '#/api/system/announcement';
import { DictTag } from '#/components';
import { DICT_TYPE } from '#/constants/dict-types';

defineOptions({ name: 'SystemAnnouncementPreview' });

const detail = ref<SystemAnnouncementApi.AnnouncementRespVO>();

const [Modal, modalApi] = useVbenModal({
  async onOpenChange(isOpen: boolean) {
    if (!isOpen) {
      detail.value = undefined;
      return;
    }

    const data = modalApi.getData() as
      | SystemAnnouncementApi.AnnouncementRespVO
      | undefined;
    if (!data?.id) {
      return;
    }

    modalApi.lock();
    try {
      detail.value = await getAnnouncement(data.id);
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal
    class="w-[760px]"
    title="公告预览"
    :show-cancel-button="false"
    :show-confirm-button="false"
  >
    <div v-if="detail" class="flex flex-col gap-4 p-2">
      <div>
        <h2 class="text-center text-xl font-semibold">
          {{ detail.title }}
        </h2>
        <div
          class="mt-2 flex flex-wrap items-center justify-center gap-3 text-sm text-muted-foreground"
        >
          <span>{{ detail.publisher || '系统公告' }}</span>
          <span v-if="detail.publishTime">
            {{ formatDateTime(detail.publishTime) }}
          </span>
          <DictTag
            :type="DICT_TYPE.SYSTEM_ANNOUNCEMENT_CATEGORY"
            :value="detail.category"
          />
          <DictTag
            :type="DICT_TYPE.SYSTEM_ANNOUNCEMENT_STATUS"
            :value="detail.status"
          />
        </div>
      </div>

      <ElDescriptions :column="2" border size="small">
        <ElDescriptionsItem label="公告编号">
          {{ detail.id }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="是否置顶">
          <DictTag
            :type="DICT_TYPE.INFRA_BOOLEAN_STRING"
            :value="detail.isTop"
          />
        </ElDescriptionsItem>
        <ElDescriptionsItem label="发布时间">
          {{ detail.publishTime ? formatDateTime(detail.publishTime) : '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="过期时间">
          {{ detail.expireTime ? formatDateTime(detail.expireTime) : '-' }}
        </ElDescriptionsItem>
      </ElDescriptions>

      <div class="rounded border p-4">
        <VbenTiptapPreview :content="detail.content" :min-height="220" />
      </div>
    </div>
  </Modal>
</template>
