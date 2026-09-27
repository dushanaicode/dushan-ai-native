<script setup lang="ts">
import type { AuthApi } from '#/api/core/auth';

import { computed, ref, watch } from 'vue';
import { useRoute } from 'vue-router';

import { SvgDingDingIcon, SvgWeChatIcon } from '@vben/icons';
import { $t } from '@vben/locales';

import { getSocialProvidersApi } from '#/api/core/auth';
import { takeErrorMessage } from '#/api/error-feedback';

import { beginSocialOAuth } from './social-oauth';

const props = defineProps<{
  disabled: boolean;
  selectTenant: boolean;
  tenantId?: string;
}>();
const route = useRoute();
const providers = ref<AuthApi.SocialProvider[]>([]);
const errorMessage = ref('');
const starting = ref(false);
const revision = ref(0);
const ready = computed(
  () =>
    import.meta.env.VITE_APP_SOCIAL_LOGIN_ENABLE === 'true' &&
    !props.disabled &&
    (!props.selectTenant || Boolean(props.tenantId)),
);

watch(
  () => {
    const tenantId = props.selectTenant ? props.tenantId : '';
    return [ready.value ? tenantId : null, revision.value];
  },
  async (_, __, onCleanup) => {
    let active = true;
    onCleanup(() => {
      active = false;
    });
    providers.value = [];
    errorMessage.value = '';
    if (!ready.value) return;
    try {
      const result = await getSocialProvidersApi(
        props.selectTenant ? props.tenantId : undefined,
      );
      if (active) providers.value = result;
    } catch (error) {
      if (active)
        errorMessage.value = takeErrorMessage(
          error,
          $t('socialLogin.loadFailed'),
        );
    }
  },
  { immediate: true, flush: 'post' },
);

async function start(provider: AuthApi.SocialProvider) {
  if (!ready.value || starting.value) return;
  starting.value = true;
  errorMessage.value = '';
  try {
    await beginSocialOAuth({
      type: provider.type,
      codeParameter: provider.codeParameter,
      tenantId: props.selectTenant ? props.tenantId : undefined,
      returnPath:
        typeof route.query.redirect === 'string' ? route.query.redirect : '',
    });
  } catch (error) {
    errorMessage.value = takeErrorMessage(error, $t('socialLogin.loadFailed'));
    starting.value = false;
  }
}
</script>

<template>
  <div v-if="providers.length || errorMessage" class="mt-4">
    <div class="flex items-center gap-4 text-xs text-muted-foreground">
      <span class="flex-1 border-b border-input"></span>
      {{ $t('authentication.thirdPartyLogin') }}
      <span class="flex-1 border-b border-input"></span>
    </div>
    <div class="mt-4 flex flex-wrap justify-center gap-4">
      <button
        v-for="provider in providers"
        :key="provider.type"
        type="button"
        :title="provider.name"
        :aria-label="provider.name"
        :disabled="starting || !ready"
        class="flex items-center gap-1 rounded px-2 py-1 hover:bg-accent disabled:opacity-50"
        @click="start(provider)"
      >
        <SvgDingDingIcon
          v-if="provider.source.startsWith('DINGTALK')"
          class="size-6"
        />
        <SvgWeChatIcon
          v-else-if="provider.source.startsWith('WECHAT')"
          class="size-6"
        />
        <span class="text-sm">{{ provider.name }}</span>
      </button>
    </div>
    <p v-if="errorMessage" role="alert" class="mt-2 text-sm text-destructive">
      {{ errorMessage }}
      <button type="button" class="ml-2 underline" @click="revision++">
        {{ $t('tenantLogin.retry') }}
      </button>
    </p>
  </div>
</template>
