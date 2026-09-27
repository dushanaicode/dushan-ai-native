<script lang="ts" setup>
import type { VbenFormSchema } from '@vben/common-ui';
import type { Recordable } from '@vben/types';

import type { AuthApi } from '#/api/core/auth';

import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';

import { AuthenticationForgetPassword, z } from '@vben/common-ui';
import { LOGIN_PATH } from '@vben/constants';
import { $t } from '@vben/locales';

import { ElMessage } from 'element-plus';

import { resetPasswordApi, sendRecoveryCodeApi } from '#/api/core/auth';
import { UnifiedCaptcha } from '#/components';
import { createCaptchaPorts } from '#/services/captcha/ports';

import { useLoginTenant } from './use-login-tenant';

defineOptions({ name: 'ForgetPassword' });
const router = useRouter();
const formRef = ref<InstanceType<typeof AuthenticationForgetPassword>>();
const captchaRef = ref<InstanceType<typeof UnifiedCaptcha>>();
const captchaPorts = createCaptchaPorts();
const { loadTenants, selectTenant, tenantError, tenantFields, tenantLoading } =
  useLoginTenant(formRef);
const channel = ref<'email' | 'sms'>('sms');
const codeLength = ref(4);
const sending = ref(false);
const loading = ref(false);
const busy = computed(
  () => sending.value || loading.value || tenantLoading.value,
);

function target(values: Recordable<any>): AuthApi.RecoveryTarget {
  return channel.value === 'sms'
    ? { channel: 'sms', mobile: values.mobile }
    : { channel: 'email', email: values.email };
}

async function sendCode() {
  const view = formRef.value;
  const captcha = captchaRef.value;
  if (busy.value || tenantError.value || !view || !captcha)
    throw new Error($t('recovery.unavailable'));
  sending.value = true;
  try {
    const form = view.getFormApi();
    const fields = ['channel', channel.value === 'sms' ? 'mobile' : 'email'];
    if (selectTenant.value) fields.push('tenantId');
    for (const field of fields) {
      await form.validateField(field);
      if (!(await form.isFieldValid(field)))
        throw new Error($t('recovery.checkFields'));
    }
    const values = await form.getValues();
    const data = target(values);
    const tenantId = selectTenant.value ? values.tenantId : undefined;
    const proof = await captcha.verify();
    codeLength.value = await sendRecoveryCodeApi(
      {
        ...data,
        verification: proof?.verification,
      },
      tenantId,
    );
    form.setFieldValue('code', '');
    ElMessage.success($t('recovery.sent'));
  } finally {
    sending.value = false;
  }
}

const formSchema = computed((): VbenFormSchema[] => [
  ...tenantFields.value.map((field) => ({
    ...field,
    componentProps: { ...field.componentProps, disabled: busy.value },
  })),
  {
    component: 'VbenSelect',
    componentProps: {
      disabled: busy.value,
      options: [
        { label: $t('recovery.sms'), value: 'sms' },
        { label: $t('recovery.email'), value: 'email' },
      ],
    },
    dependencies: {
      triggerFields: ['channel'],
      resolve({ actions, values }) {
        if (
          (values.channel === 'sms' || values.channel === 'email') &&
          values.channel !== channel.value
        ) {
          channel.value = values.channel;
          codeLength.value = values.channel === 'sms' ? 4 : 6;
          actions.setFieldValue('code', '');
        }
        return {};
      },
    },
    fieldName: 'channel',
    label: $t('recovery.channel'),
    rules: z.enum(['sms', 'email']).default('sms'),
  },
  channel.value === 'sms'
    ? {
        component: 'VbenInput',
        fieldName: 'mobile',
        label: $t('authentication.mobile'),
        componentProps: {
          disabled: busy.value,
          autocomplete: 'tel',
          placeholder: $t('recovery.mobileTip'),
        },
        rules: z.string().regex(/^1[3-9]\d{9}$/, {
          message: $t('authentication.mobileErrortip'),
        }),
      }
    : {
        component: 'VbenInput',
        fieldName: 'email',
        label: $t('authentication.email'),
        componentProps: {
          disabled: busy.value,
          autocomplete: 'email',
          placeholder: $t('recovery.emailTip'),
        },
        rules: z.string().email($t('authentication.emailValidErrorTip')),
      },
  {
    component: 'VbenPinInput',
    fieldName: 'code',
    label: $t('authentication.code'),
    componentProps: {
      codeLength: codeLength.value,
      loading: sending.value,
      disabled:
        loading.value || tenantLoading.value || Boolean(tenantError.value),
      createText: (countdown: number) =>
        countdown > 0
          ? $t('authentication.sendText', [countdown])
          : $t('authentication.sendCode'),
      handleSendCode: sendCode,
    },
    rules: z.string().length(codeLength.value, {
      message: $t('authentication.codeTip', [codeLength.value]),
    }),
  },
  {
    component: 'VbenInputPassword',
    fieldName: 'password',
    label: $t('recovery.password'),
    componentProps: {
      autocomplete: 'new-password',
      placeholder: $t('recovery.password'),
      passwordStrength: true,
    },
    rules: z
      .string()
      .min(4, { message: $t('recovery.passwordRule') })
      .max(16, { message: $t('recovery.passwordRule') }),
  },
  {
    component: 'VbenInputPassword',
    fieldName: 'confirmPassword',
    label: $t('authentication.confirmPassword'),
    componentProps: {
      autocomplete: 'new-password',
      placeholder: $t('authentication.confirmPassword'),
    },
    dependencies: {
      triggerFields: ['password'],
      resolve({ values }) {
        return {
          rules: z
            .string()
            .min(1)
            .refine((value) => value === values.password, {
              message: $t('authentication.confirmPasswordTip'),
            }),
        };
      },
    },
  },
]);

async function handleSubmit(values: Recordable<any>) {
  if (busy.value || tenantError.value) return;
  const data = {
    ...target(values),
    code: values.code,
    password: values.password,
  };
  loading.value = true;
  try {
    await resetPasswordApi(
      data,
      selectTenant.value ? values.tenantId : undefined,
    );
    ElMessage.success($t('recovery.success'));
    await router.replace(LOGIN_PATH);
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div>
    <AuthenticationForgetPassword
      ref="formRef"
      :form-schema="formSchema"
      :loading="loading || tenantLoading"
      :sub-title="$t('recovery.subtitle')"
      :submit-button-text="$t('recovery.submit')"
      @submit="handleSubmit"
    />
    <div v-if="tenantError" role="alert" class="text-destructive mt-3 text-sm">
      {{ tenantError }}
      <button type="button" class="ml-2 underline" @click="loadTenants">
        {{ $t('tenantLogin.retry') }}
      </button>
    </div>
    <UnifiedCaptcha
      ref="captchaRef"
      :ports="captchaPorts"
      purpose="password_reset"
      mode="dialog"
    />
  </div>
</template>
