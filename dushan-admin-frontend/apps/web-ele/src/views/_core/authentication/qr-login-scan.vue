<script setup lang="ts">
import type { QrLoginScan } from '#/api/core/qr-login';

import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { useUserStore } from '@vben/stores';

import { ElButton, ElCard, ElMessage } from 'element-plus';

import { getLoginTenantsApi } from '#/api/core/auth';
import {
  confirmQrLogin,
  isQrLoginEnabled,
  scanQrLogin,
} from '#/api/core/qr-login';
import { notifyError } from '#/api/error-feedback';
import { $t } from '#/locales';
import { isMobileWeb, parseQrLoginUrl } from '#/services/qr-login';
import { useTenantStore } from '#/store/tenant';

defineOptions({ name: 'QrLoginScan' });
const router = useRouter();
const route = useRoute();
const users = useUserStore();
const tenants = useTenantStore();
const mobile = isMobileWeb();
const enabled = ref(false);
const tenantName = ref<string>();
const loading = ref(false);
const scanning = ref(false);
const details = ref<QrLoginScan>();
const completed = ref<'approved' | 'cancelled'>();
const video = ref<HTMLVideoElement>();
const canvas = document.createElement('canvas');
const secureContext = window.isSecureContext;
const cameraSupported =
  secureContext && Boolean(navigator.mediaDevices?.getUserMedia);
const ticket = computed(() =>
  typeof route.query.ticket === 'string' ? route.query.ticket : undefined,
);
let stream: MediaStream | undefined;
let frame = 0;
let lastFrame = 0;
let cameraGeneration = 0;
let generation = 0;

function stopCamera() {
  cameraGeneration++;
  cancelAnimationFrame(frame);
  stream?.getTracks().forEach((track) => track.stop());
  stream = undefined;
  if (video.value) video.value.srcObject = null;
  scanning.value = false;
}

async function openCode(text: string) {
  let target;
  try {
    target = parseQrLoginUrl(
      text,
      router.resolve({ name: 'QrLoginScan' }).href,
    );
  } catch {
    ElMessage.error($t('qrLogin.invalidCode'));
    return;
  }
  await router.replace({ name: 'QrLoginScan', query: target });
}

async function startCamera() {
  stopCamera();
  const version = cameraGeneration;
  loading.value = true;
  try {
    const library = await import('jsqr');
    const jsQR = library.default;
    if (version !== cameraGeneration) return;
    const target = video.value;
    const context = canvas.getContext('2d', { willReadFrequently: true });
    if (!target || !context) throw new Error($t('qrLogin.cameraUnavailable'));
    const media = await navigator.mediaDevices.getUserMedia({
      audio: false,
      video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 } },
    });
    if (version !== cameraGeneration) {
      media.getTracks().forEach((track) => track.stop());
      return;
    }
    stream = media;
    scanning.value = true;
    target.srcObject = media;
    await target.play();
    const read = (time: number) => {
      if (!stream || !video.value) return;
      if (video.value.readyState >= 2 && time - lastFrame > 180) {
        lastFrame = time;
        canvas.width = Math.min(video.value.videoWidth, 800);
        canvas.height = Math.round(
          (video.value.videoHeight * canvas.width) / video.value.videoWidth,
        );
        context.drawImage(video.value, 0, 0, canvas.width, canvas.height);
        const image = context.getImageData(0, 0, canvas.width, canvas.height);
        const code = jsQR(image.data, image.width, image.height, {
          inversionAttempts: 'dontInvert',
        });
        if (code) {
          stopCamera();
          void openCode(code.data).catch(notifyError);
          return;
        }
      }
      frame = requestAnimationFrame(read);
    };
    frame = requestAnimationFrame(read);
  } catch (error) {
    stopCamera();
    const message =
      error instanceof DOMException && error.name === 'NotAllowedError'
        ? $t('qrLogin.cameraDenied')
        : $t('qrLogin.cameraUnavailable');
    notifyError(error, message);
  } finally {
    loading.value = false;
  }
}

async function load() {
  const version = ++generation;
  stopCamera();
  details.value = undefined;
  completed.value = undefined;
  if (!mobile) return;
  loading.value = true;
  try {
    const [qrEnabled, tenantConfig] = await Promise.all([
      isQrLoginEnabled(),
      getLoginTenantsApi(),
    ]);
    if (generation !== version) return;
    enabled.value = qrEnabled;
    tenantName.value = tenantConfig.enabled
      ? tenantConfig.tenants.find((item) => item.id === tenants.currentTenantId)
          ?.name
      : undefined;
    if (!enabled.value || !ticket.value) return;
    if (
      !/^[\w-]{43}$/.test(ticket.value) ||
      typeof route.query.tenantId !== 'string'
    ) {
      ElMessage.error($t('qrLogin.invalidCode'));
      return;
    }
    const result = await scanQrLogin(ticket.value);
    if (generation === version) details.value = result;
  } catch (error) {
    notifyError(error);
  } finally {
    if (generation === version) loading.value = false;
  }
}

async function confirm(approve: boolean) {
  if (!ticket.value) return;
  loading.value = true;
  try {
    await confirmQrLogin(ticket.value, approve);
    completed.value = approve ? 'approved' : 'cancelled';
    details.value = undefined;
  } catch (error) {
    details.value = undefined;
    notifyError(error);
  } finally {
    loading.value = false;
  }
}

function visibility() {
  if (document.hidden) stopCamera();
}
document.addEventListener('visibilitychange', visibility);
watch(() => route.fullPath, load, { immediate: true });
onBeforeUnmount(() => {
  generation++;
  stopCamera();
  document.removeEventListener('visibilitychange', visibility);
});
</script>

<template>
  <main class="bg-background min-h-dvh px-4 py-6">
    <section class="mx-auto max-w-md">
      <h1 class="mb-2 text-2xl font-semibold">
        {{ $t(ticket ? 'qrLogin.scanTitle' : 'qrLogin.scan') }}
      </h1>
      <div class="text-muted-foreground mb-6 space-y-1">
        <p>
          {{
            $t('qrLogin.signedInAs', {
              name: users.userInfo?.realName || users.userInfo?.username,
            })
          }}
        </p>
        <p v-if="tenantName">
          {{ $t('qrLogin.organization', { name: tenantName }) }}
        </p>
      </div>
      <ElCard v-if="!mobile" shadow="never">
        <p>{{ $t('qrLogin.mobileOnly') }}</p>
      </ElCard>
      <ElCard v-else-if="!enabled && !loading" shadow="never">
        <p>{{ $t('qrLogin.disabled') }}</p>
      </ElCard>
      <div v-else v-loading="loading" class="min-h-32 space-y-4">
        <ElCard v-if="details" shadow="never">
          <h2 class="text-xl font-medium">{{ $t('qrLogin.confirmTitle') }}</h2>
          <p class="text-muted-foreground mt-3 text-sm">
            {{ $t('qrLogin.confirmHint') }}
          </p>
          <div
            class="text-primary my-6 text-center font-mono text-4xl font-semibold tracking-[0.3em]"
          >
            {{ details.code }}
          </div>
          <p class="text-muted-foreground break-words text-sm">
            {{ details.browser }}
          </p>
          <p class="text-muted-foreground mb-6 text-sm">
            {{ $t('qrLogin.computerIp', { ip: details.ip }) }}
          </p>
          <div class="flex gap-3">
            <ElButton
              type="primary"
              class="flex-1"
              :disabled="loading"
              @click="confirm(true)"
            >
              {{ $t('qrLogin.confirm') }}
            </ElButton>
            <ElButton :disabled="loading" @click="confirm(false)">
              {{ $t('qrLogin.cancel') }}
            </ElButton>
          </div>
        </ElCard>
        <ElCard v-else-if="completed" shadow="never">
          <p class="text-lg font-medium">
            {{ $t(`qrLogin.result.${completed}`) }}
          </p>
          <ElButton
            class="mt-5 w-full"
            @click="router.replace({ name: 'QrLoginScan' })"
          >
            {{ $t('qrLogin.scanAnother') }}
          </ElButton>
        </ElCard>
        <ElCard v-else shadow="never">
          <p class="mb-5">
            {{
              cameraSupported
                ? $t('qrLogin.cameraHint')
                : $t(
                    secureContext
                      ? 'qrLogin.cameraUnsupported'
                      : 'qrLogin.httpsRequired',
                  )
            }}
          </p>
          <ElButton
            v-if="cameraSupported && !scanning"
            type="primary"
            class="w-full"
            :disabled="loading"
            @click="startCamera"
          >
            {{ $t('qrLogin.scan') }}
          </ElButton>
          <ElButton v-else-if="scanning" class="w-full" @click="stopCamera">
            {{ $t('qrLogin.stopCamera') }}
          </ElButton>
          <ElButton v-if="ticket" class="!ml-0 mt-3 w-full" @click="load">
            {{ $t('qrLogin.retry') }}
          </ElButton>
          <p class="text-muted-foreground mt-4 text-sm">
            {{ $t('qrLogin.browserSessionHint') }}
          </p>
        </ElCard>
        <video
          ref="video"
          v-show="scanning"
          autoplay
          muted
          playsinline
          class="w-full rounded-xl bg-black"
          :aria-label="$t('qrLogin.scan')"
        ></video>
      </div>
      <ElButton class="mt-6 w-full" @click="router.push({ name: 'Profile' })">
        {{ $t('qrLogin.backToProfile') }}
      </ElButton>
    </section>
  </main>
</template>
