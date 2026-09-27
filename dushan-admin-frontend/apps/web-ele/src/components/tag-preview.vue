<script setup lang="ts">
import type { TagStyle } from '../services/dictionary/types';
import type { TagVariant } from './tag-style';

import { computed } from 'vue';

import { ElTag } from 'element-plus';

import { tagPresentation } from './tag-style';

const props = withDefaults(
  defineProps<{
    colorType?: null | string;
    tagStyle?: null | TagStyle;
    text: string;
    variant?: TagVariant;
  }>(),
  { colorType: 'primary', tagStyle: null, variant: 'light' },
);
const style = computed(() =>
  tagPresentation(props.tagStyle, props.colorType || 'primary', props.variant),
);
</script>

<template>
  <ElTag :style="style" class="dict-tag">{{ text }}</ElTag>
</template>

<style scoped>
.dict-tag {
  font-size: 13px;
  font-weight: 500;
}
</style>
