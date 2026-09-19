<script lang="ts" setup>
import type { InfoCardData } from '../data';

import { IconifyIcon } from '@vben/icons';

import { ElCard } from 'element-plus';

import { formatCellValue } from '../data';

defineOptions({ name: 'InfraServerInfoCard' });

defineProps<{
  card: InfoCardData;
}>();
</script>

<template>
  <ElCard class="h-full" shadow="never">
    <template #header>
      <div class="flex min-h-8 items-center gap-2">
        <span
          class="flex size-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary"
        >
          <IconifyIcon :icon="card.icon" class="size-5" />
        </span>
        <span class="min-w-0 truncate text-base font-semibold">
          {{ card.title }}
        </span>
      </div>
    </template>

    <div class="grid gap-2 sm:grid-cols-2">
      <div
        v-for="item in card.items"
        :key="item.label"
        :class="item.span === 2 ? 'sm:col-span-2' : ''"
        class="rounded-md border border-border bg-muted/20 px-3 py-2"
      >
        <div class="text-xs text-muted-foreground">{{ item.label }}</div>
        <div class="mt-1 break-all text-sm font-medium text-foreground">
          {{ formatCellValue(item.value) }}
        </div>
      </div>
    </div>
  </ElCard>
</template>
