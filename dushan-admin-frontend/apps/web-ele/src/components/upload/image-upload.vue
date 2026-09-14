<script setup lang="ts">
import type { FileUploadProps, FileValue } from './files';

import { useTemplateRef } from 'vue';

import FileUpload from './file-upload.vue';

defineOptions({ inheritAttrs: false });
withDefaults(defineProps<FileUploadProps>(), {
  accept: 'image/*',
  listType: 'picture-card',
  maxNumber: 1,
  maxSize: 5,
  showDescription: true,
  showFileList: true,
});
const emit = defineEmits<{
  change: [value: FileValue];
  error: [error: unknown];
}>();
const model = defineModel<FileValue>();
const upload = useTemplateRef<InstanceType<typeof FileUpload>>('upload');
defineExpose({ cancel: () => upload.value?.cancel() });
</script>

<template>
  <FileUpload
    ref="upload"
    v-model="model"
    v-bind="$attrs"
    :ports="ports"
    :accept="accept"
    :button-text="buttonText"
    :disabled="disabled"
    :help-text="helpText"
    :list-type="listType"
    :max-number="maxNumber"
    :max-size="maxSize"
    :multiple="multiple"
    :show-description="showDescription"
    :show-file-list="showFileList"
    @change="(value) => emit('change', value)"
    @error="(error) => emit('error', error)"
  >
    <template v-if="$slots.default" #default><slot></slot></template>
  </FileUpload>
</template>
