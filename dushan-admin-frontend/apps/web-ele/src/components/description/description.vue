<script setup lang="ts">
import type { DescriptionsItemType } from '@vben/common-ui';

import type { DescriptionsOptions } from './types';

import { computed, toValue } from 'vue';

import { VbenDescriptions } from '@vben/common-ui';

const props = withDefaults(defineProps<DescriptionsOptions>(), {
  schema: () => [],
});
const data = computed(() => toValue(props.data) ?? {});
const items = computed<DescriptionsItemType[]>(() =>
  props.schema
    .filter((item) =>
      typeof item.hidden === 'function'
        ? !item.hidden(data.value)
        : !item.hidden,
    )
    .map((item, index) => ({
      key: item.field ?? index,
      label: () => item.label,
      contentStyle: item.contentStyle,
      labelStyle: item.labelStyle,
      span: item.span,
      content: () => {
        const value =
          typeof item.content === 'function'
            ? item.content(data.value)
            : (item.content ??
              (item.field ? data.value[item.field] : undefined));
        if (value === null || value === undefined || value === '') return '—';
        return typeof value === 'boolean' || typeof value === 'number'
          ? String(value)
          : value;
      },
    })),
);
</script>

<template>
  <VbenDescriptions v-bind="componentProps" :items="items" />
</template>
