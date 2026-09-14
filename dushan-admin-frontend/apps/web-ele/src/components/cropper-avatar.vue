<script setup lang="ts">
import type { ButtonProps } from 'element-plus';

import type { FileAccess, FilePorts, StoredFile } from './upload/files';

import { onUnmounted, ref, useTemplateRef, watch } from 'vue';

import { VCropper } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { ElAlert, ElButton, ElDialog } from 'element-plus';

import { uploadCroppedAvatar } from './upload/avatar';
import { parseFileAccess, validateFile } from './upload/files';

const props = withDefaults(
  defineProps<{
    ports: FilePorts;
    btnProps?: Partial<ButtonProps>;
    btnText?: string;
    showBtn?: boolean;
    size?: number;
    width?: number | string;
    disabled?: boolean;
  }>(),
  {
    btnProps: () => ({}),
    btnText: undefined,
    showBtn: true,
    size: 5,
    width: 120,
  },
);
const emit = defineEmits<{
  change: [file: StoredFile];
  error: [error: unknown];
}>();
const value = defineModel<string>('value', { default: '' });
const input = useTemplateRef<HTMLInputElement>('input');
const cropper = useTemplateRef<InstanceType<typeof VCropper>>('cropper');
const visible = ref(false);
const source = ref('');
const preview = ref('');
const busy = ref(false);
const failed = ref(false);
let accessController = new AbortController();
let uploadController = new AbortController();
watch(
  () => [value.value, props.ports] as const,
  async () => {
    close();
    accessController.abort();
    accessController = new AbortController();
    const signal = accessController.signal;
    preview.value = '';
    const id = value.value;
    if (!id) return;
    try {
      const files = parseFileAccess(await props.ports.resolve([id], signal), [
        id,
      ]);
      signal.throwIfAborted();
      preview.value = (files[0] as FileAccess).url;
    } catch (error) {
      if (!signal.aborted) report(error);
    }
  },
  { immediate: true },
);
function report(error: unknown) {
  failed.value = true;
  emit('error', error);
}
function clearSource() {
  if (source.value) URL.revokeObjectURL(source.value);
  source.value = '';
}
function close() {
  uploadController.abort();
  busy.value = false;
  visible.value = false;
  clearSource();
}
function choose(event: Event) {
  const element = event.target as HTMLInputElement;
  const file = element.files?.[0];
  element.value = '';
  if (!file || props.disabled || busy.value) return;
  try {
    validateFile(file, {
      accept: 'image/*',
      maxSize: props.size,
      maxNumber: 1,
    });
    close();
    failed.value = false;
    source.value = URL.createObjectURL(file);
    visible.value = true;
  } catch (error) {
    report(error);
  }
}
async function submit() {
  if (busy.value || props.disabled) return;
  busy.value = true;
  failed.value = false;
  uploadController.abort();
  uploadController = new AbortController();
  const signal = uploadController.signal;
  try {
    const stored = await uploadCroppedAvatar({
      cropper: cropper.value as InstanceType<typeof VCropper>,
      ports: props.ports,
      maxSize: props.size,
      signal,
    });
    value.value = stored.id;
    emit('change', stored);
    close();
  } catch (error) {
    if (!signal.aborted) report(error);
  } finally {
    if (signal === uploadController.signal) busy.value = false;
  }
}
onUnmounted(() => {
  close();
  accessController.abort();
});
</script>

<template>
  <div :style="{ width: typeof width === 'number' ? `${width}px` : width }">
    <input
      ref="input"
      type="file"
      accept="image/*"
      class="hidden"
      :disabled="disabled || busy"
      @change="choose"
    />
    <button
      type="button"
      class="bg-muted aspect-square w-full overflow-hidden rounded-full"
      :disabled="disabled || busy"
      :aria-label="$t('utils.avatar.choose')"
      @click="input?.click()"
    >
      <img
        v-if="preview"
        :src="preview"
        :alt="$t('utils.avatar.title')"
        class="h-full w-full object-cover"
      />
      <span v-else>{{ $t('utils.avatar.choose') }}</span>
    </button>
    <ElButton
      v-if="showBtn"
      v-bind="btnProps"
      :disabled="disabled || busy"
      class="mt-2"
      @click="input?.click()"
    >
      <span>{{ btnText ?? $t('utils.avatar.choose') }}</span>
    </ElButton>
    <ElAlert
      v-if="failed"
      :title="$t('utils.avatar.failed')"
      type="error"
      :closable="false"
    />
    <ElDialog
      :model-value="visible"
      :title="$t('utils.avatar.title')"
      width="min(560px, 95vw)"
      append-to-body
      @update:model-value="
        (open) => {
          if (!open) close();
        }
      "
    >
      <VCropper
        v-if="visible && source"
        ref="cropper"
        :img="source"
        aspect-ratio="1:1"
        :width="480"
        :height="360"
      />
      <ElAlert
        v-if="failed"
        :title="$t('utils.avatar.failed')"
        type="error"
        :closable="false"
      />
      <template #footer>
        <ElButton @click="close">
          <span>{{ $t('utils.avatar.cancel') }}</span>
        </ElButton>
        <ElButton
          type="primary"
          :loading="busy"
          :disabled="!source || disabled"
          @click="submit"
        >
          <span>{{ $t('utils.avatar.apply') }}</span>
        </ElButton>
      </template>
    </ElDialog>
  </div>
</template>
