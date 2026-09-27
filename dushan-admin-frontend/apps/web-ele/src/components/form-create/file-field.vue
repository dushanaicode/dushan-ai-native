<script setup lang="ts">
import { FileUpload, ImageUpload } from '#/components';
import { createFilePorts } from '#/services/file/ports';
defineOptions({ name: 'NativeFileField', inheritAttrs: false });
withDefaults(defineProps<{ image?: boolean; multiple?: boolean }>(), {
  image: false,
  multiple: false,
});
const ports = createFilePorts();
</script>

<template>
  <component
    :is="image ? ImageUpload : FileUpload"
    :multiple="multiple"
    :max-number="multiple ? 9 : 1"
    v-bind="$attrs"
    :ports="ports"
  />
</template>
