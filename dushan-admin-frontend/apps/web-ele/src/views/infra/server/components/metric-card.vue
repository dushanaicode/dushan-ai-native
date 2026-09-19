<script lang="ts" setup>
import type { MetricCardData } from '../data';

import { computed } from 'vue';

import { IconifyIcon } from '@vben/icons';

import { ElCard, ElProgress } from 'element-plus';

import { formatCellValue, getPercentStatus } from '../data';

defineOptions({ name: 'InfraServerMetricCard' });

const props = defineProps<{
  card: MetricCardData;
}>();

const usageStatus = computed(() => getPercentStatus(props.card.usage));
const secondaryStatus = computed(() =>
  props.card.secondary
    ? getPercentStatus(props.card.secondary.usage)
    : undefined,
);
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

    <div class="space-y-4">
      <div class="grid gap-4 sm:grid-cols-2">
        <div class="space-y-2">
          <div class="text-sm text-muted-foreground">
            {{ card.usageLabel }}
          </div>
          <ElProgress
            :percentage="card.usage"
            :status="usageStatus"
            :stroke-width="10"
          />
        </div>

        <div v-if="card.secondary" class="space-y-2">
          <div class="text-sm text-muted-foreground">
            {{ card.secondary.label }}
          </div>
          <ElProgress
            :percentage="card.secondary.usage"
            :status="secondaryStatus"
            :stroke-width="10"
          />
        </div>
      </div>

      <div class="grid gap-2 sm:grid-cols-2">
        <div
          v-for="item in card.items"
          :key="item.label"
          class="rounded-md border border-border bg-muted/20 px-3 py-2"
        >
          <div class="text-xs text-muted-foreground">{{ item.label }}</div>
          <div
            :class="item.danger ? 'text-destructive' : 'text-foreground'"
            class="mt-1 truncate text-sm font-medium"
          >
            {{ formatCellValue(item.value) }}{{ item.suffix || '' }}
          </div>
        </div>
      </div>
    </div>
  </ElCard>
</template>
