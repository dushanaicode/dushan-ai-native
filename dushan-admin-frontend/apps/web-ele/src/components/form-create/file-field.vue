<script setup lang="ts">
import { computed } from 'vue';

import { FileUpload, ImageUpload } from '#/components';
import { createFilePorts } from '#/services/file/ports';
defineOptions({ name: 'NativeFileField', inheritAttrs: false });
const props = withDefaults(
  defineProps<{ image?: boolean; multiple?: boolean }>(),
  {
    image: false,
    multiple: false,
  },
);
const ports = computed(() =>
  createFilePorts(props.image ? 'form-image' : 'form-file'),
);
</script>

<template>
  <component
    :is="image ? ImageUpload : FileUpload"
    :multiple="multiple"
    :max-number="multiple ? 9 : 1"
    :max-size="image ? 10 : 20"
    v-bind="$attrs"
    :ports="ports"
  />
</template>
