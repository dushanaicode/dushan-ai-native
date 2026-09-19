<script lang="ts" setup>
import type { EchartsUIType } from '@vben/plugins/echarts';

import type { CommandChartItem, CommandRow } from '../data';

import { onMounted, ref, watch } from 'vue';

import { IconifyIcon } from '@vben/icons';
import { EchartsUI, useEcharts } from '@vben/plugins/echarts';

import { ElCard, ElTable, ElTableColumn } from 'element-plus';

defineOptions({ name: 'InfraRedisMonitorCommands' });

const props = defineProps<{
  chartData: CommandChartItem[];
  rows: CommandRow[];
}>();

const chartRef = ref<EchartsUIType>();
const { renderEcharts } = useEcharts(chartRef);

function renderChart() {
  renderEcharts({
    legend: {
      bottom: 0,
      type: 'scroll',
    },
    series: [
      {
        data: props.chartData,
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.2)',
            shadowOffsetX: 0,
          },
        },
        name: '调用次数',
        radius: ['35%', '65%'],
        type: 'pie',
      },
    ],
    tooltip: {
      formatter: '{a}<br />{b}: {c} ({d}%)',
      trigger: 'item',
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
          <IconifyIcon icon="lucide:terminal" class="size-5" />
        </span>
        <span class="min-w-0 truncate text-base font-semibold">命令统计</span>
      </div>
    </template>

    <div class="grid gap-3 xl:grid-cols-[minmax(0,1fr)_360px]">
      <EchartsUI ref="chartRef" height="320px" />

      <ElTable :data="rows.slice(0, 12)" border stripe>
        <ElTableColumn label="命令" min-width="120" prop="command" />
        <ElTableColumn
          align="right"
          label="调用次数"
          prop="calls"
          width="110"
        />
        <ElTableColumn align="right" label="耗时(us)" prop="usec" width="110" />
      </ElTable>
    </div>
  </ElCard>
</template>
