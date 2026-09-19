<script lang="ts" setup>
import { Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';

import { ElAlert, ElButton, ElSkeleton } from 'element-plus';

import DiskCard from './components/disk-card.vue';
import InfoCard from './components/info-card.vue';
import MetricCard from './components/metric-card.vue';
import { useServerMonitor } from './composables/use-server-monitor';

defineOptions({ name: 'InfraServer' });

const {
  cpuCard,
  diskRows,
  errorMessage,
  isDataLoaded,
  lastUpdatedText,
  loading,
  memoryCard,
  pythonInfoCard,
  refreshServerMonitor,
  refreshing,
  serverInfoCard,
} = useServerMonitor();
</script>

<template>
  <Page auto-content-height>
    <div class="space-y-4 p-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="min-w-0">
          <h2 class="text-lg font-semibold text-foreground">服务监控</h2>
          <div v-if="lastUpdatedText" class="text-sm text-muted-foreground">
            最后更新：{{ lastUpdatedText }}
          </div>
        </div>

        <ElButton
          :loading="loading || refreshing"
          type="primary"
          @click="refreshServerMonitor()"
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
        <div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <MetricCard :card="cpuCard" />
          <MetricCard :card="memoryCard" />
          <InfoCard :card="serverInfoCard" />
          <InfoCard :card="pythonInfoCard" />
        </div>

        <DiskCard :rows="diskRows" />
      </template>
    </div>
  </Page>
</template>
