<script lang="ts" setup>
import type { FileObject, PreviewType } from '../typing';

import { computed, ref, watch } from 'vue';

import { Loading } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import { ElAlert, ElDialog } from 'element-plus';

import { takeErrorMessage } from '#/api/error-feedback';
import { resolveFileUrl } from '#/services/file/file-access';

import { getPreviewType } from '../typing';

defineOptions({ name: 'FilePreviewDialog' });

const props = defineProps<{
  file: FileObject | null;
  modelValue: boolean;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
});

const previewType = computed<PreviewType>(() =>
  props.file ? getPreviewType(props.file.type) : 'none',
);

const textContent = ref('');
const previewUrl = ref('');
const loading = ref(false);
const failed = ref('');

watch(
  () => [props.file, props.modelValue] as const,
  async ([file, open], _, onCleanup) => {
    const controller = new AbortController();
    const { signal } = controller;
    onCleanup(() => controller.abort());
    textContent.value = '';
    previewUrl.value = '';
    failed.value = '';
    loading.value = false;
    if (!open || !file?.url) {
      return;
    }

    loading.value = true;
    try {
      const url = await resolveFileUrl(file.url, signal);
      signal.throwIfAborted();
      previewUrl.value = url;
      if (getPreviewType(file.type) === 'text') {
        const response = await fetch(url, { signal });
        if (!response.ok) throw new Error('无法加载文件内容');
        const text = await response.text();
        signal.throwIfAborted();
        textContent.value = text;
      }
    } catch (error) {
      if (!signal.aborted)
        failed.value = takeErrorMessage(error, '无法加载文件内容');
    } finally {
      if (!signal.aborted) loading.value = false;
    }
  },
  { immediate: true },
);
</script>

<template>
  <ElDialog
    v-model="visible"
    append-to-body
    destroy-on-close
    :title="file?.name || '文件预览'"
    top="5vh"
    width="80%"
  >
    <ElAlert v-if="failed" type="error" :title="failed" :closable="false" />
    <Loading v-else-if="loading" spinning aria-busy="true" class="min-h-40" />
    <div v-else-if="file && previewUrl" class="preview-body">
      <div v-if="previewType === 'image'" class="preview-image">
        <img :alt="file.name" :src="previewUrl" />
      </div>

      <div v-else-if="previewType === 'video'" class="preview-video">
        <video autoplay controls :src="previewUrl">
          您的浏览器不支持视频播放
        </video>
      </div>

      <div v-else-if="previewType === 'audio'" class="preview-audio">
        <IconifyIcon icon="lucide:file-audio" class="preview-audio__icon" />
        <div class="preview-audio__name">{{ file.name }}</div>
        <audio autoplay controls :src="previewUrl">
          您的浏览器不支持音频播放
        </audio>
      </div>

      <div v-else-if="previewType === 'pdf'" class="preview-pdf">
        <iframe :src="previewUrl" sandbox=""></iframe>
      </div>

      <div v-else-if="previewType === 'text'" class="preview-text">
        <pre>{{ textContent }}</pre>
      </div>

      <div v-else class="preview-unsupported">
        <IconifyIcon icon="lucide:file" class="preview-unsupported__icon" />
        <p>该文件类型暂不支持预览</p>
        <a
          class="preview-unsupported__link"
          :href="previewUrl"
          :download="file.name"
          rel="noreferrer"
        >
          下载文件
        </a>
      </div>
    </div>
  </ElDialog>
</template>
