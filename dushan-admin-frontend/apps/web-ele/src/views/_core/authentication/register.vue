<script lang="ts" setup>
import type { VbenFormSchema } from '@vben/common-ui';
import type { Recordable } from '@vben/types';

import { computed, h, ref } from 'vue';

import { AuthenticationRegister, z } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { ElMessage } from 'element-plus';

import { isRegistrationEnabled } from '#/api/core/auth';
import { UnifiedCaptcha } from '#/components';
import { createCaptchaPorts } from '#/services/captcha/ports';
import { useAuthStore } from '#/store';

import { useLoginTenant } from './use-login-tenant';

defineOptions({ name: 'Register' });

const authStore = useAuthStore();
const formRef = ref<InstanceType<typeof AuthenticationRegister>>();
const captchaRef = ref<InstanceType<typeof UnifiedCaptcha>>();
const captchaPorts = createCaptchaPorts();
const { loadTenants, selectTenant, tenantError, tenantFields, tenantLoading } =
  useLoginTenant(formRef);
const submitting = ref(false);

const formSchema = computed((): VbenFormSchema[] => {
  return [
    ...tenantFields.value,
    {
      component: 'VbenInput',
      componentProps: {
        placeholder: $t('authentication.usernameTip'),
      },
      fieldName: 'username',
      label: $t('authentication.username'),
      rules: z.string().regex(/^[a-zA-Z0-9]{4,30}$/, {
        message: $t('registration.usernameRule'),
      }),
    },
    {
      component: 'VbenInput',
      componentProps: { placeholder: $t('registration.nicknameTip') },
      fieldName: 'nickname',
      label: $t('registration.nickname'),
      rules: z
        .string()
        .min(1, { message: $t('registration.nicknameTip') })
        .max(30, { message: $t('registration.nicknameTip') }),
    },
    {
      component: 'VbenInputPassword',
      componentProps: {
        passwordStrength: true,
        placeholder: $t('authentication.password'),
      },
      fieldName: 'password',
      label: $t('authentication.password'),
      renderComponentContent() {
        return {
          strengthText: () => $t('authentication.passwordStrength'),
        };
      },
      rules: z
        .string()
        .min(4, { message: $t('registration.passwordRule') })
        .max(16, { message: $t('registration.passwordRule') }),
    },
    {
      component: 'VbenInputPassword',
      componentProps: {
        placeholder: $t('authentication.confirmPassword'),
      },
      dependencies: {
        resolve({ values }) {
          const { password } = values;
          return {
            rules: z
              .string({ error: $t('authentication.passwordTip') })
              .min(1, { message: $t('authentication.passwordTip') })
              .refine((value) => value === password, {
                message: $t('authentication.confirmPasswordTip'),
              }),
          };
        },
        triggerFields: ['password'],
      },
      fieldName: 'confirmPassword',
      label: $t('authentication.confirmPassword'),
    },
    {
      component: 'VbenCheckbox',
      fieldName: 'agreePolicy',
      renderComponentContent: () => ({
        default: () =>
          h('span', [
            $t('authentication.agree'),
            h(
              'a',
              {
                class: 'vben-link ml-1 ',
                href: '',
              },
              `${$t('authentication.privacyPolicy')} & ${$t('authentication.terms')}`,
            ),
          ]),
      }),
      rules: z.boolean().refine((value) => !!value, {
        message: $t('authentication.agreeTip'),
      }),
    },
  ];
});

async function handleSubmit(values: Recordable<any>) {
  const captcha = captchaRef.value;
  if (submitting.value || tenantLoading.value || tenantError.value || !captcha)
    return;
  const tenantId = selectTenant.value ? values.tenantId : undefined;
  const credentials = {
    username: values.username,
    nickname: values.nickname,
    password: values.password,
  };
  submitting.value = true;
  try {
    if (!(await isRegistrationEnabled())) {
      ElMessage.error($t('registration.disabled'));
      return;
    }
    let proof;
    try {
      proof = await captcha.verify();
    } catch {
      return;
    }
    await authStore.authRegister(
      { ...credentials, verification: proof?.verification },
      tenantId,
    );
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div>
    <AuthenticationRegister
      ref="formRef"
      :form-schema="formSchema"
      :loading="submitting || tenantLoading"
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
      purpose="register"
      mode="dialog"
    />
  </div>
</template>
