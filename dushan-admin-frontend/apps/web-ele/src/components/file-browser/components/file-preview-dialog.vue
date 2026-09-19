<script lang="ts" setup>
import type { FileObject, PreviewType } from '../typing';

import { computed, ref, watch } from 'vue';

import { IconifyIcon } from '@vben/icons';

import { ElDialog } from 'element-plus';

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
const textLoading = ref(false);

watch(
  () => props.file,
  async (file) => {
    textContent.value = '';
    if (!file?.url || getPreviewType(file.type) !== 'text') {
      return;
    }

    textLoading.value = true;
    try {
      const response = await fetch(file.url);
      textContent.value = await response.text();
    } catch {
      textContent.value = '无法加载文件内容';
    } finally {
      textLoading.value = false;
    }
  },
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
    <div v-if="file?.url" class="preview-body">
      <div v-if="previewType === 'image'" class="preview-image">
        <img :alt="file.name" :src="file.url" />
      </div>

      <div v-else-if="previewType === 'video'" class="preview-video">
        <video autoplay controls :src="file.url">
          您的浏览器不支持视频播放
        </video>
      </div>

      <div v-else-if="previewType === 'audio'" class="preview-audio">
        <IconifyIcon icon="lucide:file-audio" class="preview-audio__icon" />
        <div class="preview-audio__name">{{ file.name }}</div>
        <audio autoplay controls :src="file.url">
          您的浏览器不支持音频播放
        </audio>
      </div>

      <div v-else-if="previewType === 'pdf'" class="preview-pdf">
        <iframe :src="file.url"></iframe>
      </div>

      <div v-else-if="previewType === 'text'" class="preview-text">
        <div v-if="textLoading" class="preview-text__loading">加载中...</div>
        <pre v-else>{{ textContent }}</pre>
      </div>

      <div v-else class="preview-unsupported">
        <IconifyIcon icon="lucide:file" class="preview-unsupported__icon" />
        <p>该文件类型暂不支持预览</p>
        <a
          class="preview-unsupported__link"
          :href="file.url"
          rel="noreferrer"
          target="_blank"
        >
          打开文件
        </a>
      </div>
    </div>
  </ElDialog>
</template>
