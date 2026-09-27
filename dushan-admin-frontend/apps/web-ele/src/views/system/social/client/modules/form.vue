<script lang="ts" setup>
import type { SystemSocialClientApi } from '#/api/system/social/client';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import {
  createSocialClient,
  getSocialClient,
  updateSocialClient,
} from '#/api/system/social/client';
import { SystemUserSocialTypeEnum, UserTypeEnum } from '#/constants/enums';
import { SwitchStatus } from '#/constants/status';
import { $t } from '#/locales';

import { useFormSchema } from '../data';

defineOptions({ name: 'SystemSocialClientForm' });

const emit = defineEmits(['success']);

interface SocialClientFormValues extends Omit<
  SystemSocialClientApi.SocialClientSaveReqVO,
  'authConfig'
> {
  authConfigJson?: string;
}

type SocialClientSavePayload = SystemSocialClientApi.SocialClientSaveReqVO;

/** 新建时给出后端契约要求的字段骨架，避免填成旧的驼峰字段被拒绝。 */
const AUTH_CONFIG_TEMPLATE = JSON.stringify(
  {
    credentials: {},
    options: {},
    pkce: false,
    redirect_uri: null,
    scopes: [],
  },
  null,
  2,
);

const formData = ref<SystemSocialClientApi.SocialClientRespVO>();

const title = computed(() =>
  formData.value?.id
    ? $t('ui.actionTitle.edit', ['社交客户端'])
    : $t('ui.actionTitle.create', ['社交客户端']),
);

function formatAuthConfig(
  authConfig?: SystemSocialClientApi.SocialClientAuthConfig,
) {
  if (!authConfig || Object.keys(authConfig).length === 0) {
    return '{}';
  }
  return JSON.stringify(authConfig, null, 2);
}

function parseAuthConfig(
  rawValue?: string,
): SystemSocialClientApi.SocialClientAuthConfig {
  const value = rawValue?.trim();
  if (!value) {
    throw new Error('认证配置不能为空，请输入 JSON 对象');
  }

  const parsed: unknown = JSON.parse(value);
  if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
    throw new Error('认证配置必须是 JSON 对象');
  }

  return parsed as SystemSocialClientApi.SocialClientAuthConfig;
}

function buildSaveData(
  values: SocialClientFormValues,
  isUpdate: boolean,
): SocialClientSavePayload {
  const {
    authConfigJson,
    clientSecret: rawClientSecret,
    id: _id,
    ...rest
  } = values;
  const authConfig = parseAuthConfig(authConfigJson);
  const isWechatEnterprise =
    rest.socialType === SystemUserSocialTypeEnum.WECHAT_ENTERPRISE.type ||
    rest.socialType === SystemUserSocialTypeEnum.WECHAT_ENTERPRISE_v2.type;
  const clientSecret = rawClientSecret?.trim();
  if (!clientSecret && !isUpdate) {
    throw new Error('请输入客户端密钥或平台私钥');
  }

  return {
    ...rest,
    agentId: isWechatEnterprise ? rest.agentId : undefined,
    authConfig,
    ...(clientSecret ? { clientSecret } : {}),
  };
}

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    formItemClass: 'col-span-1',
    labelWidth: 120,
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

    const values = (await formApi.getValues()) as SocialClientFormValues;
    const isUpdate = Boolean(formData.value?.id);
    let data: SocialClientSavePayload;
    try {
      data = buildSaveData(values, isUpdate);
    } catch (error) {
      ElMessage.error((error as Error).message);
      return;
    }

    modalApi.lock();
    try {
      await (isUpdate && formData.value
        ? updateSocialClient({ ...data, id: formData.value.id })
        : createSocialClient(
            data as SystemSocialClientApi.SocialClientSaveReqVO,
          ));
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
      await formApi.reset();
      return;
    }

    await formApi.reset();
    const data = modalApi.getData() as
      | SystemSocialClientApi.SocialClientRespVO
      | undefined;
    if (!data?.id) {
      await formApi.setValues({
        authConfigJson: AUTH_CONFIG_TEMPLATE,
        status: SwitchStatus.DISABLED,
        userType: UserTypeEnum.ADMIN,
      });
      return;
    }

    modalApi.lock();
    try {
      formData.value = await getSocialClient(data.id);
      await formApi.setValues({
        ...formData.value,
        authConfigJson: formatAuthConfig(formData.value.authConfig),
        clientSecret: '',
      });
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal class="w-1/2" :title="title">
    <Form class="mx-4" />
  </Modal>
</template>
