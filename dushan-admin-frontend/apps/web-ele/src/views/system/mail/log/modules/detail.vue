<script lang="ts" setup>
import type { SystemMailLogApi } from '#/api/system/mail/log';

import { ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { VbenTiptapPreview } from '@vben/plugins/tiptap';
import { formatDateTime } from '@vben/utils';

import { ElDescriptions, ElDescriptionsItem } from 'element-plus';

import { getMailLog } from '#/api/system/mail/log';
import { DictTag } from '#/components';
import { DICT_TYPE } from '#/constants/dict-types';

defineOptions({ name: 'SystemMailLogDetail' });

const detail = ref<SystemMailLogApi.MailLogRespVO>();

function formatJson(value?: Record<string, any>) {
  if (!value || Object.keys(value).length === 0) {
    return '-';
  }
  return JSON.stringify(value, null, 2);
}

const [Modal, modalApi] = useVbenModal({
  async onOpenChange(isOpen: boolean) {
    if (!isOpen) {
      detail.value = undefined;
      return;
    }

    const data = modalApi.getData() as
      | SystemMailLogApi.MailLogRespVO
      | undefined;
    if (!data?.id) {
      return;
    }

    modalApi.lock();
    try {
      detail.value = await getMailLog(data.id);
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal
    class="w-[860px]"
    title="邮件日志详情"
    :show-cancel-button="false"
    :show-confirm-button="false"
  >
    <div v-if="detail" class="flex flex-col gap-4 p-2">
      <ElDescriptions :column="2" border size="small" title="发送信息">
        <ElDescriptionsItem label="日志编号">
          {{ detail.id }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="发送状态">
          <DictTag
            :type="DICT_TYPE.SYSTEM_MAIL_SEND_STATUS"
            :value="detail.sendStatus"
          />
        </ElDescriptionsItem>
        <ElDescriptionsItem label="发送时间">
          {{ detail.sendTime ? formatDateTime(detail.sendTime) : '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="创建时间">
          {{ detail.createTime ? formatDateTime(detail.createTime) : '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="消息编号" :span="2">
          {{ detail.sendMessageId || '-' }}
        </ElDescriptionsItem>
      </ElDescriptions>

      <ElDescriptions :column="2" border size="small" title="邮箱信息">
        <ElDescriptionsItem label="邮箱账号编号">
          {{ detail.accountId }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="发件邮箱">
          {{ detail.fromMail || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="收件邮箱" :span="2">
          <span class="break-all">{{ detail.toMail || '-' }}</span>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="抄送邮箱" :span="2">
          <span class="break-all">{{ detail.ccMail || '-' }}</span>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="密送邮箱" :span="2">
          <span class="break-all">{{ detail.bccMail || '-' }}</span>
        </ElDescriptionsItem>
      </ElDescriptions>

      <ElDescriptions :column="2" border size="small" title="模板信息">
        <ElDescriptionsItem label="模板编号">
          {{ detail.templateId }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="模板编码">
          {{ detail.templateCode || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="模板昵称">
          {{ detail.templateNickname || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="模板标题">
          {{ detail.templateTitle || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="模板参数" :span="2">
          <pre class="whitespace-pre-wrap text-xs leading-5">{{
            formatJson(detail.templateParams)
          }}</pre>
        </ElDescriptionsItem>
      </ElDescriptions>

      <ElDescriptions :column="2" border size="small" title="用户信息">
        <ElDescriptionsItem label="用户编号">
          {{ detail.userId ?? '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="用户类型">
          <DictTag :type="DICT_TYPE.USER_TYPE" :value="detail.userType" />
        </ElDescriptionsItem>
      </ElDescriptions>

      <div class="rounded border p-4">
        <VbenTiptapPreview
          :content="detail.templateContent || ''"
          :min-height="220"
        />
      </div>

      <ElDescriptions
        v-if="detail.sendException"
        :column="1"
        border
        size="small"
        title="异常信息"
      >
        <ElDescriptionsItem label="异常内容">
          <pre class="whitespace-pre-wrap text-xs leading-5 text-red-500">{{
            detail.sendException
          }}</pre>
        </ElDescriptionsItem>
      </ElDescriptions>
    </div>
  </Modal>
</template>
