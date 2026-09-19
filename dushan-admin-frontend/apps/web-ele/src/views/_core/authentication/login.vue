<script lang="ts" setup>
import type { VbenFormSchema } from '@vben/common-ui';
import type { Recordable } from '@vben/types';

import { computed, ref } from 'vue';

import { AuthenticationLogin, z } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { ElMessage } from 'element-plus';

import { UnifiedCaptcha as UnifiedCaptchaComponent } from '#/components';
import { createCaptchaPorts } from '#/services/captcha/ports';
import { useAuthStore } from '#/store';

defineOptions({ name: 'Login' });

const authStore = useAuthStore();
const captchaRef = ref<InstanceType<typeof UnifiedCaptchaComponent>>();
const captchaPorts = createCaptchaPorts();

const formSchema = computed((): VbenFormSchema[] => {
  return [
    {
      component: 'VbenInput',
      componentProps: {
        placeholder: $t('authentication.usernameTip'),
      },
      fieldName: 'username',
      label: $t('authentication.username'),
      rules: z.string().min(1, { message: $t('authentication.usernameTip') }),
    },
    {
      component: 'VbenInputPassword',
      componentProps: {
        placeholder: $t('authentication.password'),
      },
      fieldName: 'password',
      label: $t('authentication.password'),
      rules: z.string().min(1, { message: $t('authentication.passwordTip') }),
    },
  ];
});

/**
 * 提交前先完成人机验证：后端验证码关闭时 acquire 立即返回 null，
 * 开启时弹出对话框，通过后将 verification 凭证随登录参数提交。
 */
async function handleSubmit(values: Recordable<any>) {
  let verification;
  try {
    verification = await captchaRef.value?.verify();
  } catch {
    // 用户取消与加载失败均由组件 error 事件呈现，此处静默中止提交
    return;
  }
  await authStore.authLogin({
    ...values,
    verification: verification?.verification,
  });
}
</script>

<template>
  <AuthenticationLogin
    :form-schema="formSchema"
    :loading="authStore.loginLoading"
    @submit="handleSubmit"
  />
  <UnifiedCaptchaComponent
    ref="captchaRef"
    :ports="captchaPorts"
    purpose="login"
    mode="dialog"
    @error="() => ElMessage.error('验证码加载失败')"
  />
</template>
