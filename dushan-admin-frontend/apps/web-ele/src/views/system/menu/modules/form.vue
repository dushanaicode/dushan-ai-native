<script lang="ts" setup>
import type { SystemMenuApi } from '#/api/system/menu';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { createMenu, getMenu, updateMenu } from '#/api/system/menu';
import { SwitchStatus } from '#/constants/status';

import { useFormSchema } from '../data';

defineOptions({ name: 'SystemMenuForm' });

const emit = defineEmits(['success']);
const formData = ref<SystemMenuApi.MenuRespVO>();

const title = computed(() =>
  formData.value?.id
    ? $t('ui.actionTitle.edit', ['菜单'])
    : $t('ui.actionTitle.create', ['菜单']),
);

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    formItemClass: 'col-span-2',
    labelWidth: 90,
  },
  layout: 'horizontal',
  schema: useFormSchema(),
  showDefaultActions: false,
});

function getDefaultValues(
  data?: Partial<SystemMenuApi.MenuRespVO & SystemMenuApi.MenuSaveReqVO>,
) {
  return {
    alwaysShow: data?.alwaysShow ?? true,
    component: data?.component,
    componentName: data?.componentName,
    icon: data?.icon,
    id: data?.id,
    keepAlive: data?.keepAlive ?? true,
    kind: data?.kind ?? 'group',
    name: data?.name,
    parentId: data?.parentId ?? '0',
    path: data?.path,
    permission: data?.permission,
    sort: data?.sort ?? 0,
    status: data?.status ?? SwitchStatus.ENABLED,
    url: data?.url,
    visible: data?.visible ?? true,
  };
}

function normalizeMenuData(
  values: SystemMenuApi.MenuSaveReqVO,
): SystemMenuApi.MenuSaveReqVO {
  const isDirOrMenu = values.kind === 'group' || values.kind === 'page';
  const isMenu = values.kind === 'page';
  const isButton = values.kind === 'action';
  const isExternal = values.kind === 'link' || values.kind === 'iframe';

  return {
    alwaysShow: isMenu ? (values.alwaysShow ?? true) : true,
    component: isMenu ? values.component : undefined,
    componentName: isMenu ? values.componentName : undefined,
    icon: isDirOrMenu ? values.icon : undefined,
    id: values.id,
    keepAlive: isMenu ? (values.keepAlive ?? true) : true,
    kind: values.kind,
    name: values.name,
    parentId: values.parentId ?? '0',
    path: isDirOrMenu ? values.path : undefined,
    permission: isMenu || isButton ? values.permission || undefined : undefined,
    sort: values.sort,
    status: values.status,
    url: isExternal ? values.url : undefined,
    visible: isDirOrMenu ? (values.visible ?? true) : true,
  };
}

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid) {
      return;
    }

    modalApi.lock();
    const values = (await formApi.getValues()) as SystemMenuApi.MenuSaveReqVO;
    const data = normalizeMenuData(values);

    try {
      await (formData.value?.id ? updateMenu(data) : createMenu(data));
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
      | Partial<SystemMenuApi.MenuSaveReqVO>
      | SystemMenuApi.MenuRespVO
      | undefined;

    if (data && 'id' in data && data.id) {
      modalApi.lock();
      try {
        formData.value = await getMenu(data.id);
        await formApi.setValues(getDefaultValues(formData.value));
      } finally {
        modalApi.unlock();
      }
      return;
    }

    formData.value = undefined;
    await formApi.setValues(getDefaultValues(data ?? undefined));
  },
});
</script>

<template>
  <Modal :title="title">
    <Form class="mx-4" />
  </Modal>
</template>
