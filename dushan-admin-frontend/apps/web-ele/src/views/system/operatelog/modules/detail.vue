<script lang="ts" setup>
import type { SystemOperateLogApi } from '#/api/system/logger/operatelog';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { formatDateTime } from '@vben/utils';

import { ElDescriptions, ElDescriptionsItem } from 'element-plus';

defineOptions({ name: 'SystemOperateLogDetail' });

const formData = ref<SystemOperateLogApi.OperateLogRespVO>();

const userInfo = computed(() => formData.value?.userInfo || {});

const deptId = computed(() => userInfo.value.deptId ?? userInfo.value.dept_id);

const loginLocation = computed(
  () => userInfo.value.loginLocation ?? userInfo.value.login_location,
);

const loginTime = computed(() => {
  const time = userInfo.value.loginTime ?? userInfo.value.login_time;
  if (
    typeof time !== 'number' &&
    typeof time !== 'string' &&
    !(time instanceof Date)
  ) {
    return '';
  }
  const numericTime = Number(time);
  return formatDateTime(
    Number.isNaN(numericTime) ? time : numericTime,
  ) as string;
});

const [Modal, modalApi] = useVbenModal({
  async onOpenChange(isOpen: boolean) {
    if (!isOpen) {
      formData.value = undefined;
      return;
    }

    const data = modalApi.getData() as
      | SystemOperateLogApi.OperateLogRespVO
      | undefined;
    if (!data?.id) {
      return;
    }

    modalApi.lock();
    try {
      formData.value = data;
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal
    class="w-[700px]"
    title="操作日志详情"
    :show-cancel-button="false"
    :show-confirm-button="false"
  >
    <div v-if="formData" class="flex flex-col gap-4 p-2">
      <ElDescriptions :column="2" border size="small" title="操作信息">
        <ElDescriptionsItem label="日志编号">
          {{ formData.id }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="链路追踪">
          {{ formData.traceId || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="操作模块">
          {{ formData.type || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="操作名">
          {{ formData.subType || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="操作内容" :span="2">
          {{ formData.action || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="formData.extra" label="拓展参数" :span="2">
          {{ formData.extra }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="业务编号">
          {{ formData.bizId ?? '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="操作时间">
          {{ formData.createTime ? formatDateTime(formData.createTime) : '-' }}
        </ElDescriptionsItem>
      </ElDescriptions>

      <ElDescriptions :column="2" border size="small" title="操作人信息">
        <ElDescriptionsItem label="昵称">
          {{ userInfo.nickname || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="用户名">
          {{ userInfo.username || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="用户编号">
          {{ formData.userId ?? '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="部门ID">
          {{ deptId ?? '-' }}
        </ElDescriptionsItem>
      </ElDescriptions>

      <ElDescriptions :column="2" border size="small" title="请求信息">
        <ElDescriptionsItem label="请求方式">
          {{ formData.requestMethod || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="请求URL">
          {{ formData.requestUrl || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="操作IP">
          {{ userInfo.ipaddr || formData.userIp || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="登录位置">
          {{ loginLocation || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="浏览器">
          {{ userInfo.browser || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="操作系统">
          {{ userInfo.os || '-' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="loginTime" label="登录时间">
          {{ loginTime }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="UserAgent" :span="2">
          <span class="break-all text-xs text-muted-foreground">
            {{ formData.userAgent || '-' }}
          </span>
        </ElDescriptionsItem>
      </ElDescriptions>
    </div>
  </Modal>
</template>
