<script setup lang="ts">
import type {
  ImageUploadOptions,
  TipTapProps,
  VbenTiptapChangeEvent,
} from '@vben/plugins/tiptap';

import { computed, onUnmounted, ref, watch } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';
import { VbenTiptap } from '@vben/plugins/tiptap';

import { ElAlert, ElButton } from 'element-plus';

import RichTextContent from './notification-content.vue';

interface RichImageUpload {
  accept?: string;
  maxSize?: number;
  upload: (
    file: File,
    signal: AbortSignal,
    onProgress?: (percent: number) => void,
  ) => Promise<string>;
}
const props = withDefaults(
  defineProps<
    Omit<TipTapProps, 'imageUpload'> & {
      disabled?: boolean;
      imageUpload?: false | RichImageUpload;
    }
  >(),
  {
    editable: true,
    toolbar: true,
    previewable: true,
    minHeight: 240,
    maxHeight: 400,
    placeholder: undefined,
    extensions: undefined,
    imageUpload: undefined,
  },
);
const emit = defineEmits<{
  error: [error: unknown];
  change: [value: VbenTiptapChangeEvent];
  pending: [value: boolean];
}>();
const model = defineModel<string>({ default: '' });
const draft = ref(model.value);
const pending = ref(false);
const activeUploads = ref(0);
let lifetime = new AbortController();
function temporaryImages(node: VbenTiptapChangeEvent['json']): boolean {
  if (
    node.type === 'image' &&
    (node.attrs?.['data-uploading'] === 'true' ||
      /^blob:/i.test(node.attrs?.src ?? ''))
  )
    return true;
  return node.content?.some((child) => temporaryImages(child)) ?? false;
}
function changed(value: VbenTiptapChangeEvent) {
  const next = temporaryImages(value.json);
  if (next !== pending.value) {
    pending.value = next;
    emit('pending', next);
  }
  if (next) return;
  model.value = value.html;
  emit('change', value);
}
function cancelUploads() {
  lifetime.abort();
  lifetime = new AbortController();
}
watch(model, (value) => {
  if (value !== draft.value) {
    cancelUploads();
    draft.value = value;
    pending.value = false;
    emit('pending', false);
  }
});
const [Modal, modal] = useVbenModal({ footer: false });
const imageUpload = computed<ImageUploadOptions | undefined>(() => {
  const port = props.imageUpload;
  if (!port) return undefined;
  return {
    accept: port.accept,
    maxSize: port.maxSize,
    onUploadError: (error) => {
      if (
        !lifetime.signal.aborted &&
        !(error instanceof DOMException && error.name === 'AbortError')
      )
        emit('error', error);
    },
    upload: async (file, onProgress) => {
      const signal = lifetime.signal;
      const canceled = Promise.withResolvers<string>();
      const abort = () =>
        canceled.reject(new DOMException('图片上传已取消', 'AbortError'));
      signal.addEventListener('abort', abort, { once: true });
      activeUploads.value += 1;
      try {
        const url = await Promise.race([
          Promise.resolve().then(() => {
            signal.throwIfAborted();
            return port.upload(file, signal, (percent) => {
              if (!signal.aborted) onProgress?.(percent);
            });
          }),
          canceled.promise,
        ]);
        signal.throwIfAborted();
        const parsed = new URL(url, window.location.origin);
        if (
          !['http:', 'https:'].includes(parsed.protocol) ||
          parsed.username ||
          parsed.password
        )
          throw new TypeError('编辑器图片必须使用持久HTTP(S)地址');
        return url;
      } catch (error) {
        signal.throwIfAborted();
        throw error;
      } finally {
        signal.removeEventListener('abort', abort);
        activeUploads.value -= 1;
      }
    },
  };
});
onUnmounted(() => {
  lifetime.abort();
  emit('pending', false);
});
defineExpose({ cancelUploads, pending });
</script>

<template>
  <div>
    <VbenTiptap
      v-model="draft"
      :editable="editable && !disabled"
      :extensions="extensions"
      :image-upload="imageUpload"
      :min-height="minHeight"
      :max-height="maxHeight"
      :placeholder="placeholder"
      :toolbar="toolbar"
      :previewable="false"
      @change="changed"
    />
    <ElAlert
      v-if="pending"
      type="info"
      :closable="false"
      :title="$t('utils.editor.pending')"
    >
      <ElButton v-if="activeUploads > 0" text @click="cancelUploads">
        <span>{{ $t('utils.upload.cancel') }}</span>
      </ElButton>
    </ElAlert>
    <ElButton v-if="previewable" text :disabled="pending" @click="modal.open()">
      <span>{{ $t('utils.editor.preview') }}</span>
    </ElButton>
    <Modal :title="$t('utils.editor.preview')">
      <RichTextContent :content="model" />
    </Modal>
  </div>
</template>
