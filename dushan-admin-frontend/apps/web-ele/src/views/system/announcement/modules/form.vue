<script lang="ts" setup>
import type { SystemAnnouncementApi } from '#/api/system/announcement';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  createAnnouncement,
  getAnnouncement,
  updateAnnouncement,
} from '#/api/system/announcement';
import { $t } from '#/locales';

import { useFormSchema } from '../data';

defineOptions({ name: 'SystemAnnouncementForm' });

const emit = defineEmits(['success']);
const formData = ref<SystemAnnouncementApi.AnnouncementRespVO>();

const title = computed(() =>
  formData.value?.id
    ? $t('ui.actionTitle.edit', ['公告'])
    : $t('ui.actionTitle.create', ['公告']),
);

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    formItemClass: 'col-span-1',
    labelWidth: 90,
  },
  layout: 'horizontal',
  schema: useFormSchema(),
  showDefaultActions: false,
  wrapperClass: 'grid-cols-2',
});

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid) {
      return;
    }

    modalApi.lock();
    const data =
      (await formApi.getValues()) as SystemAnnouncementApi.AnnouncementSaveReqVO;

    try {
      await (formData.value?.id
        ? updateAnnouncement(data)
        : createAnnouncement(data));
      await modalApi.close();
      emit('success');
      ElMessage.success($t('ui.actionMessage.operationSuccess'));
    } finally {
      modalApi.unlock();
    }
  },
  async onOpenChange(isOpen: boolean) {
    if (!isOpen) {
      formData.value = undefined;
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
      formData.value = await getAnnouncement(data.id);
      await formApi.setValues(formData.value);
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal class="w-[760px]" :title="title">
    <Form class="mx-4" />
  </Modal>
</template>
