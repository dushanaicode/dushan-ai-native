<script lang="ts" setup>
import type { SystemOAuth2ClientApi } from '#/api/system/oauth2/client';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  createOAuth2Client,
  getOAuth2Client,
  updateOAuth2Client,
} from '#/api/system/oauth2/client';
import { UserTypeEnum } from '#/constants/enums';
import { SwitchStatus } from '#/constants/status';
import { $t } from '#/locales';

import { useFormSchema } from '../data';

defineOptions({ name: 'SystemOAuth2ClientForm' });

const emit = defineEmits(['success']);
const formData = ref<SystemOAuth2ClientApi.OAuth2ClientRespVO>();

type OAuth2ClientFormValues = SystemOAuth2ClientApi.OAuth2ClientSaveReqVO;

const title = computed(() =>
  formData.value?.id
    ? $t('ui.actionTitle.edit', ['OAuth2 客户端'])
    : $t('ui.actionTitle.create', ['OAuth2 客户端']),
);

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    formItemClass: 'col-span-1',
    labelWidth: 140,
  },
  layout: 'horizontal',
  schema: useFormSchema(),
  showDefaultActions: false,
});

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid) {
      return;
    }

    modalApi.lock();
    const values = (await formApi.getValues()) as OAuth2ClientFormValues;
    const { id: _id, secret, ...clientFields } = values;
    const rotatedSecret = secret?.trim();
    const existingClientId = formData.value?.id;

    try {
      if (existingClientId) {
        await updateOAuth2Client({
          ...clientFields,
          ...(rotatedSecret ? { secret: rotatedSecret } : {}),
          id: existingClientId,
        });
      } else {
        if (!rotatedSecret) {
          ElMessage.error('创建客户端时必须填写强客户端密钥');
          return;
        }
        await createOAuth2Client({
          ...clientFields,
          secret: rotatedSecret,
        });
      }
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
      await formApi.resetForm();
      return;
    }

    await formApi.resetForm();
    const data = modalApi.getData() as
      | SystemOAuth2ClientApi.OAuth2ClientRespVO
      | undefined;
    if (!data?.id) {
      await formApi.setValues({
        accessTokenValiditySeconds: 1800,
        authorities: [],
        authorizedGrantTypes: [],
        autoApproveScopes: [],
        redirectUris: [],
        refreshTokenValiditySeconds: 2_592_000,
        resourceIds: [],
        scopes: [],
        status: SwitchStatus.ENABLED,
        userType: UserTypeEnum.ADMIN,
      });
      return;
    }

    modalApi.lock();
    try {
      formData.value = await getOAuth2Client(data.id);
      await formApi.setValues({
        ...formData.value,
        authorities: formData.value.authorities ?? [],
        autoApproveScopes: formData.value.autoApproveScopes ?? [],
        resourceIds: formData.value.resourceIds ?? [],
        scopes: formData.value.scopes ?? [],
        secret: '',
        userType: UserTypeEnum.ADMIN,
      });
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal class="w-2/3" :title="title">
    <Form class="mx-4" />
  </Modal>
</template>
