<script setup lang="ts">
import type {
  CaptchaAnswer,
  CaptchaChallenge,
} from '../../services/captcha/schema';

import { onMounted, onUnmounted, useTemplateRef } from 'vue';

import { $t } from '@vben/locales';
import { preferences } from '@vben/preferences';

import { mountCloudCaptcha } from '../../services/captcha/cloud';

const props = defineProps<{
  challenge: Extract<CaptchaChallenge, { provider: 'aliyun' | 'tencent' }>;
  verify: (answer: CaptchaAnswer) => Promise<unknown>;
}>();
const emit = defineEmits<{ cancel: []; error: [error: unknown] }>();
const element = useTemplateRef<HTMLElement>('element');
const button = useTemplateRef<HTMLButtonElement>('button');
const id = `captcha-${crypto.randomUUID()}`;
const controller = new AbortController();
let release: (() => void) | undefined;
onMounted(async () => {
  try {
    release = await mountCloudCaptcha({
      challenge: props.challenge,
      element: element.value as HTMLElement,
      button: button.value as HTMLButtonElement,
      signal: controller.signal,
      language: preferences.app.locale.toLowerCase(),
      verify: props.verify,
      cancel: () => emit('cancel'),
      onError: (error) => emit('error', error),
    });
  } catch (error) {
    if (!controller.signal.aborted) emit('error', error);
  }
});
onUnmounted(() => {
  controller.abort();
  release?.();
});
</script>

<template>
  <div>
    <div :id="`${id}-element`" ref="element"></div>
    <button
      :id="`${id}-button`"
      ref="button"
      type="button"
      class="rounded-md border border-border px-4 py-2 disabled:opacity-50"
    >
      {{ $t('utils.captcha.begin') }}
    </button>
  </div>
</template>
