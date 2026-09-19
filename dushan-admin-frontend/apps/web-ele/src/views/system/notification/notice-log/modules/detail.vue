<script lang="ts" setup>
import type { SystemNoticeLogApi } from '#/api/system/notification/notice-log';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { formatDateTime } from '@vben/utils';

import {
  ElDescriptions,
  ElDescriptionsItem,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus';

import { getNoticeLogDetail } from '#/api/system/notification/notice-log';
import { DictTag } from '#/components';
import { DICT_TYPE } from '#/constants/dict-types';

defineOptions({ name: 'SystemNoticeLogDetail' });

const detail = ref<SystemNoticeLogApi.NoticeLogDetailRespVO>();

const publisherInfo = computed(() => detail.value?.publisherInfo || {});
const messages = computed(() => detail.value?.messages || []);
const targetDeptNames = computed(() => detail.value?.targetDeptNames || []);
const targetUserIds = computed(() => detail.value?.targetUserIds || []);

const [Modal, modalApi] = useVbenModal({
  async onOpenChange(isOpen: boolean) {
    if (!isOpen) {
      detail.value = undefined;
      return;
    }

    const data = modalApi.getData() as
      | SystemNoticeLogApi.NoticeLogRespVO
      | undefined;
    if (!data?.id) {
      return;
    }

    modalApi.lock();
    try {
      detail.value = await getNoticeLogDetail(data.id);
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal
    class="w-[860px]"
    title="推送日志详情"
    :show-cancel-button="false"
    :show-confirm-button="false"
  >
    <div v-if="detail" class="flex flex-col gap-4 p-2">
      <ElDescriptions :column="2" border size="small" title="通知信息">
        <ElDescriptionsItem label="日志编号">
          {{ detail.id }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="通知编号">
          {{ detail.noticeId }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="通知标题" :span="2">
          {{ detail.noticeTitle }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="通知类型">
          <DictTag
            :type="DICT_TYPE.SYSTEM_NOTICE_TYPE"
            :value="detail.noticeType"
          />
        </ElDescriptionsItem>
        <ElDescriptionsItem label="推送目标">
          <DictTag
            :type="DICT_TYPE.SYSTEM_PUSH_TARGET_TYPE"
            :value="detail.pushTargetType"
          />
        </ElDescriptionsItem>
        <ElDescriptionsItem label="推送渠道" :span="2">
          <div class="flex flex-wrap gap-1">
            <DictTag
              v-for="channel in detail.pushChannels"
              :key="channel"
              :type="DICT_TYPE.SYSTEM_NOTIFICATION_CHANNEL"
              :value="channel"
            />
          </div>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="推送状态">
          <DictTag
            :type="DICT_TYPE.SYSTEM_NOTICE_PUSH_STATUS"
            :value="detail.pushStatus"
          />
        </ElDescriptionsItem>
        <ElDescriptionsItem label="创建时间">
          {{ detail.createTime ? formatDateTime(detail.createTime) : '-' }}
        </ElDescriptionsItem>
      </ElDescriptions>

      <ElDescriptions :column="3" border size="small" title="推送结果">
        <ElDescriptionsItem label="总数">
          {{ detail.totalCount }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="成功数">
          {{ detail.successCount }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="失败数">
          {{ detail.failCount }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="目标部门" :span="3">
          <div class="flex flex-wrap gap-1">
            <ElTag
              v-for="deptName in targetDeptNames"
              :key="deptName"
              size="small"
              type="info"
            >
              {{ deptName }}
            </ElTag>
            <span v-if="targetDeptNames.length === 0">-</span>
          </div>
        </ElDescriptionsItem>
        <ElDescriptionsItem label="目标用户" :span="3">
          <div class="flex flex-wrap gap-1">
            <ElTag
              v-for="userId in targetUserIds"
              :key="userId"
              size="small"
              type="info"
            >
              #{{ userId }}
            </ElTag>
            <span v-if="targetUserIds.length === 0">-</span>
          </div>
        </ElDescriptionsItem>
      </ElDescriptions>

      <ElDescriptions :column="2" border size="small" title="发布人">
        <ElDescriptionsItem label="昵称">
          {{ publisherInfo.nickname || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="账号">
          {{ publisherInfo.username || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="浏览器">
          {{ publisherInfo.browser || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="操作系统">
          {{ publisherInfo.os || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="IP">
          {{ publisherInfo.ipaddr || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="部门ID">
          {{ publisherInfo.deptId ?? '-' }}
        </ElDescriptionsItem>
      </ElDescriptions>

      <ElTable :data="messages" border size="small">
        <ElTableColumn label="消息编号" prop="id" width="110" />
        <ElTableColumn label="用户编号" prop="userId" width="110" />
        <ElTableColumn label="账号" prop="username" min-width="130" />
        <ElTableColumn label="昵称" prop="nickname" min-width="130" />
        <ElTableColumn label="用户类型" width="110">
          <template #default="{ row }">
            <DictTag :type="DICT_TYPE.USER_TYPE" :value="row.userType" />
          </template>
        </ElTableColumn>
        <ElTableColumn label="已读状态" width="110">
          <template #default="{ row }">
            <DictTag
              :type="DICT_TYPE.INFRA_BOOLEAN_STRING"
              :value="row.readStatus"
            />
          </template>
        </ElTableColumn>
        <ElTableColumn label="阅读时间" min-width="170">
          <template #default="{ row }">
            {{ row.readTime ? formatDateTime(row.readTime) : '-' }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="创建时间" min-width="170">
          <template #default="{ row }">
            {{ row.createTime ? formatDateTime(row.createTime) : '-' }}
          </template>
        </ElTableColumn>
      </ElTable>
    </div>
  </Modal>
</template>
