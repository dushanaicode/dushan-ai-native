import type { InfraRedisMonitorApi } from '#/api/infra/redis-monitor';

import { computed, onMounted, onUnmounted, ref } from 'vue';

import { getCacheMonitorInfo } from '#/api/infra/redis-monitor';

import {
  normalizeRedisMonitor,
  REDIS_MONITOR_REFRESH_INTERVAL,
  useCommandChartData,
  useCommandRows,
  useInfoItems,
  useMemoryChartData,
  useMemoryMetrics,
} from '../data';

export function useRedisMonitor() {
  const rawData = ref<InfraRedisMonitorApi.MonitorRespVO>();
  const errorMessage = ref('');
  const loading = ref(false);
  const refreshing = ref(false);
  const lastUpdatedAt = ref<Date>();
  let refreshTimer: null | number = null;

  const isDataLoaded = computed(() => Boolean(lastUpdatedAt.value));
  const redisData = computed(() => normalizeRedisMonitor(rawData.value));
  const infoItems = computed(() => useInfoItems(redisData.value));
  const memoryMetrics = computed(() => useMemoryMetrics(redisData.value));
  const memoryChartData = computed(() => useMemoryChartData(redisData.value));
  const commandRows = computed(() => useCommandRows(redisData.value));
  const commandChartData = computed(() => useCommandChartData(redisData.value));
  const lastUpdatedText = computed(() => {
    if (!lastUpdatedAt.value) {
      return '';
    }
    return lastUpdatedAt.value.toLocaleTimeString();
  });

  async function refreshRedisMonitor(silent = false) {
    if (loading.value || refreshing.value) {
      return;
    }

    if (silent) {
      refreshing.value = true;
    } else {
      loading.value = true;
    }

    try {
      rawData.value = await getCacheMonitorInfo();
      lastUpdatedAt.value = new Date();
      errorMessage.value = '';
    } catch {
      errorMessage.value = 'Redis 监控数据加载失败';
    } finally {
      loading.value = false;
      refreshing.value = false;
    }
  }

  function startRefreshTimer() {
    stopRefreshTimer();
    refreshTimer = window.setInterval(() => {
      void refreshRedisMonitor(true);
    }, REDIS_MONITOR_REFRESH_INTERVAL);
  }

  function stopRefreshTimer() {
    if (refreshTimer === null) {
      return;
    }
    window.clearInterval(refreshTimer);
    refreshTimer = null;
  }

  onMounted(() => {
    void refreshRedisMonitor();
    startRefreshTimer();
  });

  onUnmounted(() => {
    stopRefreshTimer();
  });

  return {
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
  };
}
