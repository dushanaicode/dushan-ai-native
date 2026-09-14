<script setup lang="ts">
import type { CaptchaPorts } from '../../services/captcha/controller';
import type { CaptchaVerification } from '../../services/captcha/schema';

import { onMounted, onUnmounted, ref } from 'vue';

import { $t } from '@vben/locales';

import { ElDialog } from 'element-plus';

import { CaptchaController } from '../../services/captcha/controller';
import CaptchaPanel from './captcha-panel.vue';

const props = withDefaults(
  defineProps<{
    ports: CaptchaPorts;
    purpose: string;
    mode?: 'dialog' | 'inline';
  }>(),
  { mode: 'dialog' },
);
const emit = defineEmits<{
  verified: [value: CaptchaVerification | null];
  cancel: [];
  error: [error: unknown];
}>();
const visible = ref(false);
const controller = new CaptchaController(props.ports, (error) =>
  emit('error', error),
);
function cancel() {
  controller.cancel();
  visible.value = false;
  emit('cancel');
}
async function verify() {
  visible.value = true;
  const verification = await controller.acquire(props.purpose);
  visible.value = false;
  emit('verified', verification);
  return verification;
}
onMounted(() => {
  if (props.mode === 'inline')
    void verify().catch((error) => {
      if (!(error instanceof DOMException && error.name === 'AbortError'))
        emit('error', error);
    });
});
onUnmounted(() => controller.dispose());
defineExpose({ verify, cancel });
</script>

<template>
  <CaptchaPanel
    v-if="mode === 'inline' && visible"
    :controller
    @cancel="cancel"
    @error="(error) => emit('error', error)"
  />
  <ElDialog
    v-else-if="mode === 'dialog'"
    :model-value="visible"
    :title="$t('utils.captcha.title')"
    width="380px"
    append-to-body
    @update:model-value="
      (open) => {
        if (!open && visible) cancel();
      }
    "
  >
    <CaptchaPanel
      v-if="visible"
      :controller
      @cancel="cancel"
      @error="(error) => emit('error', error)"
    />
  </ElDialog>
</template>
