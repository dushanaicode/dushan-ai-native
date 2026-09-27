<script setup lang="ts">
import type { VbenFormSchema } from '@vben/common-ui';
import type { Recordable } from '@vben/types';

import type { SocialOAuthContext } from './social-oauth';

import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { AuthenticationLogin, z } from '@vben/common-ui';
import { LOGIN_PATH } from '@vben/constants';
import { $t } from '@vben/locales';
import { useUserStore } from '@vben/stores';

import { BusinessError } from '#/api/business-error';
import { takeErrorMessage } from '#/api/error-feedback';
import { bindSocialUser } from '#/api/system/social/user';
import { UnifiedCaptcha } from '#/components';
import { createCaptchaPorts } from '#/services/captcha/ports';
import { getSession } from '#/services/session/runtime';
import { useAuthStore } from '#/store';
import { useTenantStore } from '#/store/tenant';

import {
  beginSocialOAuth,
  consumeSocialContext,
  socialCallbackCode,
} from './social-oauth';

defineOptions({ name: 'SocialLogin' });
const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const tenants = useTenantStore();
const users = useUserStore();
const captcha = ref<InstanceType<typeof UnifiedCaptcha>>();
const ports = createCaptchaPorts();
const context = ref<SocialOAuthContext>();
const needsBinding = ref(false);
const busy = ref(false);
const failure = ref('');
const formSchema = computed((): VbenFormSchema[] => [
  {
    component: 'VbenInput',
    fieldName: 'username',
    label: $t('authentication.username'),
    componentProps: { placeholder: $t('authentication.usernameTip') },
    rules: z.string().min(1, $t('authentication.usernameTip')),
  },
  {
    component: 'VbenInputPassword',
    fieldName: 'password',
    label: $t('authentication.password'),
    componentProps: { placeholder: $t('authentication.password') },
    rules: z.string().min(1, $t('authentication.passwordTip')),
  },
]);

async function finish() {
  const oauthContext = context.value;
  const user = users.userInfo;
  if (!oauthContext || !user) throw new Error($t('socialLogin.sessionChanged'));
  await router.replace(oauthContext.returnPath || user.homePath);
}

onMounted(async () => {
  try {
    const state = z.string().min(1).parse(route.query.state);
    context.value = consumeSocialContext(state);
    if (route.query.error !== undefined) {
      failure.value = $t('socialLogin.denied');
      return;
    }
    const data = {
      type: context.value.type,
      state,
      code: socialCallbackCode(context.value.codeParameter, route.query),
    };
    if (context.value.bindingAccountId) {
      const session = getSession().capture();
      if (session.token === null) {
        failure.value = $t('socialLogin.sessionChanged');
        return;
      }
      const user = await auth.fetchUserInfo();
      getSession().assertCurrent(session);
      if (
        String(user.userId) !== context.value.bindingAccountId ||
        tenants.currentTenantId !== context.value.tenantId
      ) {
        failure.value = $t('socialLogin.sessionChanged');
        return;
      }
      await bindSocialUser(data, session);
      await finish();
    } else {
      await auth.authSocialLogin(data, finish);
    }
  } catch (error) {
    if (error instanceof BusinessError && error.code === 1_002_000_005) {
      needsBinding.value = true;
    } else {
      failure.value = takeErrorMessage(error, $t('socialLogin.failed'));
    }
  }
});

async function bindAccount(values: Recordable<any>) {
  const oauthContext = context.value;
  const challenge = captcha.value;
  if (busy.value || !oauthContext || !challenge) return;
  busy.value = true;
  failure.value = '';
  const credentials = { username: values.username, password: values.password };
  try {
    let proof;
    try {
      proof = await challenge.verify();
    } catch {
      return;
    }
    await auth.authLogin(
      { ...credentials, verification: proof?.verification },
      oauthContext.tenantId,
      async () => {
        // 原授权码已经消费；验证本站账号后重新授权，用新码绑定当前会话。
        const user = users.userInfo;
        const tenantId = tenants.currentTenantId;
        if (!user || tenantId === null) {
          throw new Error($t('socialLogin.sessionChanged'));
        }
        await beginSocialOAuth({
          ...oauthContext,
          tenantId,
          bindingAccountId: String(user.userId),
        });
      },
    );
  } catch (error) {
    failure.value = takeErrorMessage(error, $t('socialLogin.failed'));
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div>
    <AuthenticationLogin
      v-if="needsBinding"
      :form-schema="formSchema"
      :loading="busy"
      :title="$t('socialLogin.bindTitle')"
      :sub-title="$t('socialLogin.bindDescription')"
      :submit-button-text="$t('socialLogin.bindAction')"
      :show-code-login="false"
      :show-forget-password="false"
      :show-qrcode-login="false"
      :show-register="false"
      :show-third-party-login="false"
      :show-remember-me="false"
      @submit="bindAccount"
    />
    <p v-else-if="!failure" role="status" class="py-10 text-center">
      {{ $t('socialLogin.processing') }}
    </p>
    <p v-if="failure" role="alert" class="my-4 text-sm text-destructive">
      {{ failure }}
    </p>
    <button
      v-if="failure || needsBinding"
      type="button"
      class="mt-4 w-full underline"
      @click="router.replace(LOGIN_PATH)"
    >
      {{ $t('authentication.goToLogin') }}
    </button>
    <UnifiedCaptcha
      ref="captcha"
      :ports="ports"
      purpose="login"
      mode="dialog"
    />
  </div>
</template>
