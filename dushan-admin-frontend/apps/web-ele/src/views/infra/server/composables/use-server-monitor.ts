import type { InfraServerApi } from '#/api/infra/server';

import { computed, onMounted, onUnmounted, ref } from 'vue';

import { getServerInfo } from '#/api/infra/server';

import {
  SERVER_MONITOR_REFRESH_INTERVAL,
  useCpuCard,
  useDiskRows,
  useMemoryCard,
  usePythonInfoCard,
  useServerInfoCard,
} from '../data';

export function useServerMonitor() {
  const server = ref<InfraServerApi.ServerMonitorRespVO>();
  const errorMessage = ref('');
  const loading = ref(false);
  const refreshing = ref(false);
  const lastUpdatedAt = ref<Date>();
  let refreshTimer: null | number = null;

  const isDataLoaded = computed(() => Boolean(lastUpdatedAt.value));
  const cpuCard = computed(() => useCpuCard(server.value));
  const memoryCard = computed(() => useMemoryCard(server.value));
  const serverInfoCard = computed(() => useServerInfoCard(server.value));
  const pythonInfoCard = computed(() => usePythonInfoCard(server.value));
  const diskRows = computed(() => useDiskRows(server.value));
  const lastUpdatedText = computed(() => {
    if (!lastUpdatedAt.value) {
      return '';
    }
    return lastUpdatedAt.value.toLocaleTimeString();
  });

  async function refreshServerMonitor(silent = false) {
    if (loading.value || refreshing.value) {
      return;
    }

    if (silent) {
      refreshing.value = true;
    } else {
      loading.value = true;
    }

    try {
      server.value = await getServerInfo();
      lastUpdatedAt.value = new Date();
      errorMessage.value = '';
    } catch {
      errorMessage.value = '服务监控数据加载失败';
    } finally {
      loading.value = false;
      refreshing.value = false;
    }
  }

  function startRefreshTimer() {
    stopRefreshTimer();
    refreshTimer = window.setInterval(() => {
      void refreshServerMonitor(true);
    }, SERVER_MONITOR_REFRESH_INTERVAL);
  }

  function stopRefreshTimer() {
    if (refreshTimer === null) {
      return;
    }
    window.clearInterval(refreshTimer);
    refreshTimer = null;
  }

  onMounted(() => {
    void refreshServerMonitor();
    startRefreshTimer();
  });

  onUnmounted(() => {
    stopRefreshTimer();
  });

  return {
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
  };
}
