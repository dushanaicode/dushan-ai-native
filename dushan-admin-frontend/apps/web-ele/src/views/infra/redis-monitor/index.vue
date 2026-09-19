<script lang="ts" setup>
import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import { ElAlert, ElButton, ElSkeleton } from 'element-plus';

import Commands from './components/commands.vue';
import Info from './components/info.vue';
import Memory from './components/memory.vue';
import { useRedisMonitor } from './composables/use-redis-monitor';

defineOptions({ name: 'InfraRedisMonitor' });

const {
  commandChartData,
  commandRows,
  errorMessage,
  infoItems,
  isDataLoaded,
  lastUpdatedText,
  loading,
  memoryChartData,
  memoryMetrics,
  refreshRedisMonitor,
  refreshing,
} = useRedisMonitor();
</script>

<template>
  <Page auto-content-height>
    <template #doc>
      <DocAlert title="Redis 缓存" url="https://doc.iocoder.cn/redis-cache/" />
      <DocAlert title="本地缓存" url="https://doc.iocoder.cn/local-cache/" />
    </template>

    <div class="space-y-4 p-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="min-w-0">
          <h2 class="text-lg font-semibold text-foreground">Redis 监控</h2>
          <div v-if="lastUpdatedText" class="text-sm text-muted-foreground">
            最后更新：{{ lastUpdatedText }}
          </div>
        </div>

        <ElButton
          :loading="loading || refreshing"
          type="primary"
          @click="refreshRedisMonitor()"
        >
          <IconifyIcon icon="lucide:refresh-cw" class="mr-1 size-4" />
          刷新
        </ElButton>
      </div>

      <ElAlert
        v-if="errorMessage"
        :closable="false"
        :title="errorMessage"
        show-icon
        type="error"
      />

      <ElSkeleton v-if="loading && !isDataLoaded" :rows="8" animated />

      <template v-else>
        <Info :items="infoItems" />

        <div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <Memory :chart-data="memoryChartData" :metrics="memoryMetrics" />
          <Commands :chart-data="commandChartData" :rows="commandRows" />
        </div>
      </template>
    </div>
  </Page>
</template>
