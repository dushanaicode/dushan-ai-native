<script lang="ts" setup>
import type { SystemSmsLogApi } from '#/api/system/sms/log';

import { ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { formatDateTime } from '@vben/utils';

import { ElDescriptions, ElDescriptionsItem } from 'element-plus';

import { DictTag } from '#/components';
import { DICT_TYPE } from '#/constants/dict-types';

defineOptions({ name: 'SystemSmsLogDetail' });

const detail = ref<SystemSmsLogApi.SmsLogRespVO>();

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

    const data = modalApi.getData() as SystemSmsLogApi.SmsLogRespVO | undefined;
    if (!data?.id) {
      return;
    }

    detail.value = data;
  },
});
</script>

<template>
  <Modal
    class="w-[860px]"
    title="短信日志详情"
    :show-cancel-button="false"
    :show-confirm-button="false"
  >
    <div v-if="detail" class="flex flex-col gap-4 p-2">
      <ElDescriptions :column="2" border size="small" title="短信信息">
        <ElDescriptionsItem label="日志编号">
          {{ detail.id }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="手机号">
          {{ detail.mobile }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="短信渠道">
          <DictTag
            :type="DICT_TYPE.SYSTEM_SMS_CHANNEL_CODE"
            :value="detail.channelCode"
          />
        </ElDescriptionsItem>
        <ElDescriptionsItem label="渠道编号">
          {{ detail.channelId }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="模板编号">
          {{ detail.templateId }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="模板编码">
          {{ detail.templateCode }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="短信类型">
          <DictTag
            :type="DICT_TYPE.SYSTEM_SMS_TEMPLATE_TYPE"
            :value="detail.templateType"
          />
        </ElDescriptionsItem>
        <ElDescriptionsItem label="API 模板编号">
          {{ detail.apiTemplateId }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="短信内容" :span="2">
          {{ detail.templateContent }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="短信参数" :span="2">
          <pre class="whitespace-pre-wrap text-xs leading-5">{{
            formatJson(detail.templateParams)
          }}</pre>
        </ElDescriptionsItem>
      </ElDescriptions>

      <ElDescriptions :column="2" border size="small" title="发送结果">
        <ElDescriptionsItem label="发送状态">
          <DictTag
            :type="DICT_TYPE.SYSTEM_SMS_SEND_STATUS"
            :value="detail.sendStatus"
          />
        </ElDescriptionsItem>
        <ElDescriptionsItem label="发送时间">
          {{ detail.sendTime ? formatDateTime(detail.sendTime) : '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="API 发送编码">
          {{ detail.apiSendCode || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="API 发送消息">
          {{ detail.apiSendMsg || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="API 请求 ID" :span="2">
          <span class="break-all">{{ detail.apiRequestId || '-' }}</span>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="API 序列号" :span="2">
          <span class="break-all">{{ detail.apiSerialNo || '-' }}</span>
        </ElDescriptionsItem>
      </ElDescriptions>

      <ElDescriptions :column="2" border size="small" title="接收结果">
        <ElDescriptionsItem label="接收状态">
          <DictTag
            :type="DICT_TYPE.SYSTEM_SMS_RECEIVE_STATUS"
            :value="detail.receiveStatus"
          />
        </ElDescriptionsItem>
        <ElDescriptionsItem label="接收时间">
          {{ detail.receiveTime ? formatDateTime(detail.receiveTime) : '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="API 接收编码">
          {{ detail.apiReceiveCode || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="API 接收消息">
          {{ detail.apiReceiveMsg || '-' }}
        </ElDescriptionsItem>
      </ElDescriptions>

      <ElDescriptions :column="2" border size="small" title="用户信息">
        <ElDescriptionsItem label="用户编号">
          {{ detail.userId ?? '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="用户类型">
          <DictTag :type="DICT_TYPE.USER_TYPE" :value="detail.userType" />
        </ElDescriptionsItem>
        <ElDescriptionsItem label="创建时间">
          {{ detail.createTime ? formatDateTime(detail.createTime) : '-' }}
        </ElDescriptionsItem>
      </ElDescriptions>
    </div>
  </Modal>
</template>
