<script lang="ts" setup>
import type { SystemNoticeApi } from '#/api/system/notification/notice';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { isEmpty } from '@vben/utils';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { pushNoticeToTargets } from '#/api/system/notification/notice';
import { $t } from '#/locales';

import { usePushTargetFormSchema } from '../data';

defineOptions({ name: 'SystemNoticePushTarget' });

const emit = defineEmits(['success']);
const notice = ref<SystemNoticeApi.NoticeRespVO>();

const title = computed(() => `推送通知：${notice.value?.title || ''}`);

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    formItemClass: 'col-span-1',
    labelWidth: 90,
  },
  layout: 'horizontal',
  schema: usePushTargetFormSchema(),
  showDefaultActions: false,
});

function toStringIds(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.map(String);
}

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    if (!notice.value?.id) {
      return;
    }

    const { valid } = await formApi.validate();
    if (!valid) {
      return;
    }

    const values = await formApi.getValues();
    const deptIds = toStringIds(values.deptIds);
    const userIds = toStringIds(values.userIds);
    if (isEmpty(deptIds) && isEmpty(userIds)) {
      ElMessage.warning('请选择目标部门或目标用户');
      return;
    }

    modalApi.lock();
    try {
      await pushNoticeToTargets({
        deptIds,
        id: notice.value.id,
        userIds,
      });
      await modalApi.close();
      emit('success');
      ElMessage.success($t('ui.actionMessage.operationSuccess'));
    } finally {
      modalApi.unlock();
    }
  },
  async onOpenChange(isOpen: boolean) {
    if (!isOpen) {
      notice.value = undefined;
      return;
    }

    notice.value = modalApi.getData() as
      | SystemNoticeApi.NoticeRespVO
      | undefined;
    await formApi.resetForm();
  },
});
</script>

<template>
  <Modal class="w-[560px]" :title="title">
    <Form class="mx-4" />
  </Modal>
</template>
