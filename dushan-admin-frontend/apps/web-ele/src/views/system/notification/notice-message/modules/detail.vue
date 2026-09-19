<script lang="ts" setup>
import type { SystemNoticeMessageApi } from '#/api/system/notification/notice-message';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { VbenTiptapPreview } from '@vben/plugins/tiptap';
import { formatDateTime } from '@vben/utils';

import { ElAvatar, ElDescriptions, ElDescriptionsItem } from 'element-plus';

import { getNoticeMessage } from '#/api/system/notification/notice-message';
import { DictTag } from '#/components';
import { DICT_TYPE } from '#/constants/dict-types';

defineOptions({ name: 'SystemNoticeMessageDetail' });

const detail = ref<SystemNoticeMessageApi.NoticeMessageRespVO>();
const publisherInfo = computed(() => detail.value?.publisherInfo || {});

const [Modal, modalApi] = useVbenModal({
  async onOpenChange(isOpen: boolean) {
    if (!isOpen) {
      detail.value = undefined;
      return;
    }

    const data = modalApi.getData() as
      | SystemNoticeMessageApi.NoticeMessageRespVO
      | undefined;
    if (!data?.id) {
      return;
    }

    modalApi.lock();
    try {
      detail.value = await getNoticeMessage(data.id);
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal
    class="w-[760px]"
    title="站内信详情"
    :show-cancel-button="false"
    :show-confirm-button="false"
  >
    <div v-if="detail" class="flex flex-col gap-4 p-2">
      <div class="flex items-center gap-3">
        <ElAvatar :size="40" :src="publisherInfo.avatar">
          {{ publisherInfo.nickname?.slice(0, 1) || '系' }}
        </ElAvatar>
        <div class="min-w-0 flex-1">
          <div class="truncate text-base font-medium">
            {{ detail.noticeTitle }}
          </div>
          <div class="mt-1 text-sm text-muted-foreground">
            {{ publisherInfo.nickname || publisherInfo.username || '系统通知' }}
            <span class="mx-2">/</span>
            {{ detail.createTime ? formatDateTime(detail.createTime) : '-' }}
          </div>
        </div>
      </div>

      <ElDescriptions :column="2" border size="small">
        <ElDescriptionsItem label="消息编号">
          {{ detail.id }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="通知编号">
          {{ detail.noticeId }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="通知类型">
          <DictTag
            :type="DICT_TYPE.SYSTEM_NOTICE_TYPE"
            :value="detail.noticeType"
          />
        </ElDescriptionsItem>
        <ElDescriptionsItem label="已读状态">
          <DictTag
            :type="DICT_TYPE.INFRA_BOOLEAN_STRING"
            :value="detail.readStatus"
          />
        </ElDescriptionsItem>
        <ElDescriptionsItem label="阅读时间">
          {{ detail.readTime ? formatDateTime(detail.readTime) : '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="创建时间">
          {{ detail.createTime ? formatDateTime(detail.createTime) : '-' }}
        </ElDescriptionsItem>
      </ElDescriptions>

      <div class="rounded border p-4">
        <VbenTiptapPreview
          :content="detail.noticeContent || ''"
          :min-height="180"
        />
      </div>
    </div>
  </Modal>
</template>
