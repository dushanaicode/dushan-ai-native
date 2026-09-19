<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type { MemoryChartItem, MemoryMetricItem } from '../data';

import { onMounted, ref, watch } from 'vue';

import { IconifyIcon } from '@vben/icons';
import { EchartsUI, useEcharts } from '@vben/plugins/echarts';

import { ElCard } from 'element-plus';

defineOptions({ name: 'InfraRedisMonitorMemory' });

const props = defineProps<{
  chartData: MemoryChartItem[];
  metrics: MemoryMetricItem[];
}>();

const chartRef = ref<EchartsUIType>();
const { renderEcharts } = useEcharts(chartRef);

function renderChart() {
  renderEcharts({
    grid: {
      bottom: 24,
      containLabel: true,
      left: 8,
      right: 16,
      top: 24,
    },
    series: [
      {
        barMaxWidth: 40,
        data: props.chartData.map((item) => Number(item.value.toFixed(2))),
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
        },
        name: '内存',
        type: 'bar',
      },
    ],
    tooltip: {
      formatter: '{b}: {c} MB',
      trigger: 'axis',
    },
    xAxis: {
      data: props.chartData.map((item) => item.name),
      type: 'category',
    },
    yAxis: {
      axisLabel: {
        formatter: '{value} MB',
      },
      type: 'value',
    },
  });
}

watch(
  () => props.chartData,
  () => renderChart(),
  { deep: true },
);

onMounted(() => renderChart());
</script>

<template>
  <ElCard class="h-full" shadow="never">
    <template #header>
      <div class="flex min-h-8 items-center gap-2">
        <span
          class="flex size-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary"
        >
          <IconifyIcon icon="lucide:memory-stick" class="size-5" />
        </span>
        <span class="min-w-0 truncate text-base font-semibold">内存使用</span>
      </div>
    </template>

    <div class="grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px]">
      <EchartsUI ref="chartRef" height="300px" />

      <div class="grid content-start gap-2">
        <div
          v-for="item in metrics"
          :key="item.label"
          class="rounded-md border border-border bg-muted/20 px-3 py-2"
        >
          <div class="text-xs text-muted-foreground">{{ item.label }}</div>
          <div class="mt-1 truncate font-mono text-sm font-semibold">
            {{ item.value }}
          </div>
        </div>
      </div>
    </div>
  </ElCard>
</template>
