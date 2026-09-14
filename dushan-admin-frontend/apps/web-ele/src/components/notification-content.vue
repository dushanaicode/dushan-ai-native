<script setup lang="ts">
import { VbenTiptap } from '@vben/plugins/tiptap';

defineProps<{ content: string }>();
</script>

<template>
  <VbenTiptap
    :model-value="content"
    :editable="false"
    :toolbar="false"
    :previewable="false"
    :min-height="0"
  />
</template>
