<script lang="ts" setup>
import type { SystemUserApi } from '#/api/system/user';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { createUser, getUser, updateUser } from '#/api/system/user';

import { useFormSchema } from '../data';

const emit = defineEmits<{
  success: [];
}>();

const formData = ref<null | SystemUserApi.UserRespVO>(null);

const title = computed(() => {
  return formData.value?.id
    ? $t('ui.actionTitle.edit', ['用户'])
    : $t('ui.actionTitle.create', ['用户']);
});

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    formItemClass: 'col-span-2',
  },
  layout: 'horizontal',
  schema: useFormSchema(),
  showDefaultActions: false,
  wrapperClass: 'grid-cols-2',
});

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid) return;

    modalApi.lock();
    try {
      const values = (await formApi.getValues()) as SystemUserApi.UserSaveReqVO;
      const data = normalizeUserValues(values);
      await (formData.value?.id ? updateUser(data) : createUser(data));
      ElMessage.success($t('ui.actionMessage.operationSuccess'));
      emit('success');
      modalApi.close();
    } finally {
      modalApi.unlock();
    }
  },
  async onOpenChange(isOpen) {
    if (!isOpen) {
      formData.value = null;
      return;
    }

    const data = modalApi.getData() as SystemUserApi.UserRespVO | undefined;
    formData.value = data ?? null;

    if (!data?.id) {
      await formApi.setValues({ postIds: [] });
      return;
    }

    modalApi.lock();
    try {
      const detail = await getUser(data.id);
      formData.value = detail;
      await formApi.setValues({
        ...detail,
        postIds: detail.postIds ?? [],
      });
    } finally {
      modalApi.unlock();
    }
  },
});

function emptyToUndefined<T>(value: '' | null | T | undefined) {
  return value === '' || value === null ? undefined : value;
}

function normalizeUserValues(
  values: SystemUserApi.UserSaveReqVO,
): SystemUserApi.UserSaveReqVO {
  const data: SystemUserApi.UserSaveReqVO = {
    ...values,
    deptId: emptyToUndefined(values.deptId),
    email: emptyToUndefined(values.email),
    mobile: emptyToUndefined(values.mobile),
    postIds: values.postIds?.length ? values.postIds : undefined,
    remark: emptyToUndefined(values.remark),
    sex: emptyToUndefined(values.sex),
  };

  if (data.id) {
    delete data.password;
  }

  return data;
}
</script>

<template>
  <Modal :title="title" class="w-1/2">
    <Form />
  </Modal>
</template>
