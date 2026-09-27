<script lang="ts" setup>
import type { AuthApi } from '#/api/core/auth';
import type { QrLoginStatus, QrLoginTicket } from '#/api/core/qr-login';

import {
  computed,
  onActivated,
  onBeforeUnmount,
  onDeactivated,
  onMounted,
  ref,
} from 'vue';
import { useRouter } from 'vue-router';

import { LOGIN_PATH } from '@vben/constants';

import { useQRCode } from '@vueuse/integrations/useQRCode';
import { ElButton, ElOption, ElSelect } from 'element-plus';

import { getLoginTenantsApi } from '#/api/core/auth';
import {
  cancelQrLogin,
  createQrLogin,
  isQrLoginEnabled,
  pollQrLogin,
} from '#/api/core/qr-login';
import { notifyError } from '#/api/error-feedback';
import { $t } from '#/locales';
import { isMobileWeb, qrLoginUrl } from '#/services/qr-login';
import { useAuthStore } from '#/store';
import { useTenantStore } from '#/store/tenant';

defineOptions({ name: 'QrCodeLogin' });
const router = useRouter();
const auth = useAuthStore();
const tenantStore = useTenantStore();
const tenants = ref<AuthApi.TenantConfig>();
const selectedTenant = ref<string>();
const ticket = ref<QrLoginTicket>();
const status = ref<'idle' | QrLoginStatus>('idle');
const loading = ref(false);
const enabled = ref(false);
const now = ref(Date.now());
let active = false;
let generation = 0;
let timer: ReturnType<typeof setTimeout> | undefined;
let clock: ReturnType<typeof setInterval> | undefined;
let pollAbort: AbortController | undefined;

const url = computed(() =>
  ticket.value
    ? qrLoginUrl(
        router.resolve({
          name: 'QrLoginScan',
          query: {
            ticket: ticket.value.ticket,
            tenantId: ticket.value.tenantId,
          },
        }).href,
      )
    : '',
);
const mobileAddress = computed(() =>
  url.value ? new URL(url.value) : undefined,
);
const loopback = computed(() =>
  ['127.0.0.1', '[::1]', 'localhost'].includes(
    mobileAddress.value?.hostname ?? '',
  ),
);
const qrcode = useQRCode(url, {
  errorCorrectionLevel: 'M',
  margin: 4,
  width: 280,
});
const remaining = computed(() =>
  ticket.value
    ? Math.max(0, Math.ceil((ticket.value.expiresAt - now.value) / 1000))
    : 0,
);
const showCode = computed(
  () => ticket.value && ['scanned', 'waiting'].includes(status.value),
);

function stop() {
  generation++;
  clearTimeout(timer);
  clearInterval(clock);
  pollAbort?.abort();
}

async function poll(current: QrLoginTicket, version: number) {
  if (!active || generation !== version) return;
  pollAbort = new AbortController();
  try {
    const result = await pollQrLogin(current.ticket, pollAbort.signal);
    if (!active || generation !== version) return;
    status.value = result.status;
    if (result.status === 'approved') {
      stop();
      try {
        await auth.authQrLogin(current.ticket);
      } catch (error) {
        status.value = 'idle';
        notifyError(error);
      }
      return;
    }
    if (['cancelled', 'expired'].includes(result.status)) {
      stop();
      return;
    }
    timer = setTimeout(() => poll(current, version), current.pollInterval);
  } catch (error) {
    if (generation !== version) return;
    stop();
    status.value = 'idle';
    notifyError(error);
  }
}

async function refresh() {
  if (loading.value || !enabled.value) return;
  if (tenants.value?.enabled && !selectedTenant.value) return;
  stop();
  const version = generation;
  loading.value = true;
  status.value = 'idle';
  const previous = ticket.value;
  ticket.value = undefined;
  try {
    if (previous && previous.expiresAt > Date.now())
      await cancelQrLogin(previous.ticket);
    const created = await createQrLogin(
      tenants.value?.enabled ? selectedTenant.value : undefined,
    );
    if (!active || generation !== version) {
      await cancelQrLogin(created.ticket);
      return;
    }
    ticket.value = created;
    status.value = 'waiting';
    now.value = Date.now();
    clock = setInterval(() => {
      now.value = Date.now();
      if (!remaining.value) {
        status.value = 'expired';
        stop();
      }
    }, 1000);
    timer = setTimeout(() => poll(created, version), created.pollInterval);
  } catch (error) {
    notifyError(error);
  } finally {
    loading.value = false;
  }
}

async function activate() {
  if (active) return;
  active = true;
  try {
    if (isMobileWeb() || !(await isQrLoginEnabled())) {
      await router.replace(LOGIN_PATH);
      return;
    }
    enabled.value = true;
    tenants.value = await getLoginTenantsApi();
    if (tenants.value.enabled) {
      if (import.meta.env.VITE_APP_TENANT_ENABLE !== 'true')
        throw new Error($t('tenantLogin.configuration'));
      const selected = tenants.value.tenants.find(
        (item) => item.id === tenantStore.lastTenantId,
      );
      selectedTenant.value =
        selected?.id ??
        (tenants.value.tenants.length === 1
          ? tenants.value.tenants[0]?.id
          : undefined);
    }
    await refresh();
  } catch (error) {
    notifyError(error);
  }
}

async function changeTenant() {
  tenantStore.lastTenantId = selectedTenant.value ?? null;
  await refresh();
}

function deactivate() {
  active = false;
  stop();
}
onMounted(activate);
onActivated(activate);
onDeactivated(deactivate);
onBeforeUnmount(deactivate);
</script>

<template>
  <section class="mx-auto w-full max-w-sm text-center">
    <h1 class="mb-3 text-3xl font-semibold">{{ $t('qrLogin.title') }}</h1>
    <p class="text-muted-foreground mb-6">{{ $t('qrLogin.subtitle') }}</p>
    <ElSelect
      v-if="tenants?.enabled"
      v-model="selectedTenant"
      class="mb-5 w-full"
      :disabled="loading"
      :placeholder="$t('tenantLogin.select')"
      @change="changeTenant"
    >
      <ElOption
        v-for="item in tenants.tenants"
        :key="item.id"
        :label="item.name"
        :value="item.id"
      />
    </ElSelect>
    <div
      v-loading="loading || auth.loginLoading"
      class="border-border flex min-h-80 flex-col items-center justify-center rounded-xl border p-5"
    >
      <img
        v-if="showCode"
        :src="qrcode"
        :alt="$t('qrLogin.title')"
        class="h-64 w-64 rounded-lg bg-white"
      />
      <p class="mt-4 font-medium" role="status">
        {{ $t(`qrLogin.status.${status}`) }}
      </p>
      <p v-if="showCode" class="text-muted-foreground mt-2 text-sm">
        {{ $t('qrLogin.code') }}
        <strong class="text-foreground font-mono tracking-widest">{{
          ticket?.code
        }}</strong>
        · {{ $t('qrLogin.remaining', { seconds: remaining }) }}
      </p>
    </div>
    <p
      v-if="mobileAddress"
      class="text-muted-foreground mt-3 break-all text-sm"
    >
      {{ $t('qrLogin.mobileAddress', { address: mobileAddress.origin }) }}
    </p>
    <p v-if="loopback" class="mt-3 text-sm text-amber-600 dark:text-amber-400">
      {{ $t('qrLogin.loopback') }}
    </p>
    <ElButton
      class="mt-5 w-full"
      type="primary"
      :loading="loading"
      :disabled="!enabled || (tenants?.enabled && !selectedTenant)"
      @click="refresh"
    >
      {{ $t('qrLogin.refresh') }}
    </ElButton>
    <ElButton
      class="!ml-0 mt-3 w-full"
      @click="
        router.push({
          path: LOGIN_PATH,
          query: router.currentRoute.value.query,
        })
      "
    >
      {{ $t('qrLogin.passwordLogin') }}
    </ElButton>
  </section>
</template>
