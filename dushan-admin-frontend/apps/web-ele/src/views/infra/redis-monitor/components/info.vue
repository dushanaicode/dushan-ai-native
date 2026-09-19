<script lang="ts" setup>
import type { InfoItem } from '../data';

import { IconifyIcon } from '@vben/icons';

import { ElCard } from 'element-plus';

defineOptions({ name: 'InfraRedisMonitorInfo' });

defineProps<{
  items: InfoItem[];
}>();
</script>

<template>
  <ElCard shadow="never">
    <template #header>
      <div class="flex min-h-8 items-center gap-2">
        <span
          class="flex size-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary"
        >
          <IconifyIcon icon="lucide:database" class="size-5" />
        </span>
        <span class="min-w-0 truncate text-base font-semibold">
          Redis 概览
        </span>
      </div>
    </template>

    <div class="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-3">
      <div
        v-for="item in items"
        :key="item.label"
        class="flex min-w-0 items-center gap-3 rounded-md border border-border bg-muted/20 px-3 py-3"
      >
        <span
          class="flex size-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary"
        >
          <IconifyIcon :icon="item.icon" class="size-5" />
        </span>
        <span class="min-w-0 flex-1">
          <span class="block truncate text-xs text-muted-foreground">
            {{ item.label }}
          </span>
          <span class="mt-1 block truncate font-mono text-sm font-semibold">
            {{ item.value }}
          </span>
        </span>
      </div>
    </div>
  </ElCard>
</template>
