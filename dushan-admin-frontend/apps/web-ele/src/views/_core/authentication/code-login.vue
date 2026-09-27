<script lang="ts" setup>
import type { VbenFormSchema } from '@vben/common-ui';
import type { Recordable } from '@vben/types';

import { computed, ref } from 'vue';

import { AuthenticationCodeLogin, z } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { ElMessage } from 'element-plus';

import { sendLoginSmsApi } from '#/api/core/auth';
import { UnifiedCaptcha as UnifiedCaptchaComponent } from '#/components';
import { createCaptchaPorts } from '#/services/captcha/ports';
import { useAuthStore } from '#/store';

import { useLoginTenant } from './use-login-tenant';

defineOptions({ name: 'CodeLogin' });

const authStore = useAuthStore();
const loginRef = ref<InstanceType<typeof AuthenticationCodeLogin>>();
const captchaRef = ref<InstanceType<typeof UnifiedCaptchaComponent>>();
const captchaPorts = createCaptchaPorts();
const { loadTenants, selectTenant, tenantError, tenantFields, tenantLoading } =
  useLoginTenant(loginRef);
const sending = ref(false);
const codeLength = ref(4);

async function sendCode() {
  const login = loginRef.value;
  const captcha = captchaRef.value;
  if (tenantLoading.value || tenantError.value || !login || !captcha)
    throw new Error(tenantError.value);
  const form = login.getFormApi();
  const fields = selectTenant.value ? ['tenantId', 'mobile'] : ['mobile'];
  for (const field of fields) {
    await form.validateField(field);
    if (!(await form.isFieldValid(field)))
      throw new Error($t('smsLogin.checkFields'));
  }
  const values = await form.getValues();
  const data = {
    mobile: values.mobile,
  };
  const tenantId = selectTenant.value ? values.tenantId : undefined;
  sending.value = true;
  try {
    const verification = await captcha.verify();
    codeLength.value = await sendLoginSmsApi(
      {
        ...data,
        verification: verification?.verification,
      },
      tenantId,
    );
    form.setFieldValue('code', '');
    ElMessage.success($t('smsLogin.ready'));
  } finally {
    sending.value = false;
  }
}

const formSchema = computed((): VbenFormSchema[] => [
  ...tenantFields.value,
  {
    component: 'VbenInput',
    componentProps: {
      placeholder: $t('authentication.mobile'),
      autocomplete: 'tel',
    },
    fieldName: 'mobile',
    label: $t('authentication.mobile'),
    rules: z
      .string()
      .regex(/^1[3-9]\d{9}$/, { message: $t('authentication.mobileErrortip') }),
  },
  {
    component: 'VbenPinInput',
    componentProps: {
      codeLength: codeLength.value,
      disabled:
        tenantLoading.value ||
        Boolean(tenantError.value) ||
        authStore.loginLoading,
      loading: sending.value,
      createText: (countdown: number) =>
        countdown > 0
          ? $t('authentication.sendText', [countdown])
          : $t('authentication.sendCode'),
      handleSendCode: sendCode,
    },
    fieldName: 'code',
    label: $t('authentication.code'),
    rules: z.string().length(codeLength.value, {
      message: $t('authentication.codeTip', [codeLength.value]),
    }),
  },
]);

async function handleLogin(values: Recordable<any>) {
  if (sending.value || tenantLoading.value || tenantError.value) return;
  await authStore.authSmsLogin(
    {
      mobile: values.mobile,
      code: values.code,
    },
    selectTenant.value ? values.tenantId : undefined,
  );
}
</script>

<template>
  <div>
    <AuthenticationCodeLogin
      ref="loginRef"
      :form-schema="formSchema"
      :loading="authStore.loginLoading || tenantLoading"
      @submit="handleLogin"
    />
    <div v-if="tenantError" role="alert" class="text-destructive mt-3 text-sm">
      {{ tenantError }}
      <button type="button" class="ml-2 underline" @click="loadTenants">
        {{ $t('tenantLogin.retry') }}
      </button>
    </div>
    <UnifiedCaptchaComponent
      ref="captchaRef"
      :ports="captchaPorts"
      purpose="login"
      mode="dialog"
    />
  </div>
</template>
