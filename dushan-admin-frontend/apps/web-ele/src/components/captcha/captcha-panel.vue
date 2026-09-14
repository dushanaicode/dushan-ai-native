<script setup lang="ts">
import type { CaptchaController } from '../../services/captcha/controller';
import type { CaptchaAnswer } from '../../services/captcha/schema';

import { computed, shallowRef } from 'vue';

import { $t } from '@vben/locales';

import { ElAlert, ElButton } from 'element-plus';

import CloudCaptcha from './cloud-captcha.vue';
import LocalCaptcha from './local-captcha.vue';

const props = defineProps<{ controller: CaptchaController }>();
const emit = defineEmits<{ cancel: []; error: [error: unknown] }>();
const localError = shallowRef<unknown>();
const challenge = computed(() => props.controller.challenge);
const busy = computed(() =>
  ['loading', 'verifying'].includes(props.controller.status),
);
function failed(error: unknown) {
  if (error instanceof DOMException && error.name === 'AbortError') return;
  localError.value = error;
  emit('error', error);
}
async function submit(answer: CaptchaAnswer) {
  try {
    await verify(answer);
  } catch (error) {
    failed(error);
  }
}
function verify(answer: CaptchaAnswer) {
  localError.value = undefined;
  return props.controller.submit(answer);
}
async function reload() {
  localError.value = undefined;
  try {
    await props.controller.reload();
  } catch (error) {
    failed(error);
  }
}
</script>

<template>
  <div class="flex flex-col items-center gap-3" :aria-busy="busy">
    <ElAlert
      v-if="controller.error || localError"
      :title="$t('utils.captcha.failed')"
      type="error"
      :closable="false"
    />
    <p v-if="busy">{{ $t('utils.captcha.loading') }}</p>
    <template v-if="challenge">
      <LocalCaptcha
        v-if="
          challenge.provider === 'block_puzzle' ||
          challenge.provider === 'click_word'
        "
        :key="challenge.token"
        :challenge
        :busy
        @answer="submit"
        @refresh="reload"
      />
      <CloudCaptcha
        v-else
        :key="challenge.token"
        :challenge
        :verify
        @cancel="emit('cancel')"
        @error="failed"
      />
    </template>
    <ElButton :disabled="busy" @click="reload">
      <span>{{ $t('utils.captcha.refresh') }}</span>
    </ElButton>
  </div>
</template>
