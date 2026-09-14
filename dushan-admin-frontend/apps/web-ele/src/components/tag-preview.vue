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
  { colorType: 'primary', tagStyle: null, variant: 'solid' },
);
const style = computed(() =>
  tagPresentation(props.tagStyle, props.colorType ?? 'primary', props.variant),
);
</script>

<template>
  <ElTag :style="style" size="small">{{ text }}</ElTag>
</template>
