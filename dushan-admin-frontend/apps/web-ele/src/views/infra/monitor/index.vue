<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue';

import { Loading, Page } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';
import { usePreferences } from '@vben/preferences';

import { ElAlert, ElButton, ElRadioButton, ElRadioGroup } from 'element-plus';

import { takeErrorMessage } from '#/api/error-feedback';
import { getConfigValueByKey } from '#/api/infra/config/data';
import { IFrame } from '#/components';
import { $t } from '#/locales';

defineOptions({ name: 'InfraMonitor' });

type MonitorType = 'jaeger' | 'tempo';

interface MonitorOption {
  label: string;
  value: MonitorType;
}

const DEFAULT_MONITOR_URLS: Record<MonitorType, string> = {
  jaeger: 'http://localhost:16686',
  tempo: 'http://localhost:3000',
};

const MONITOR_CONFIG_KEYS: Record<MonitorType, string> = {
  jaeger: 'url.jaeger',
  tempo: 'url.tempo',
};

const monitorOptions: MonitorOption[] = [
  { label: 'Jaeger 监控', value: 'jaeger' },
  { label: 'Tempo 监控', value: 'tempo' },
];

const errorMessage = ref('');
const loading = ref(false);
const initialized = ref(false);
const frame = ref<InstanceType<typeof IFrame>>();
const monitorType = ref<MonitorType>('jaeger');
const { isDark } = usePreferences();
const monitorUrls = ref<Record<MonitorType, string>>({
  ...DEFAULT_MONITOR_URLS,
});

const currentSrc = computed(
  () =>
    monitorUrls.value[monitorType.value] ||
    DEFAULT_MONITOR_URLS[monitorType.value],
);
const frameSrc = computed(() => {
  if (monitorType.value !== 'jaeger') return currentSrc.value;
  // Jaeger的UIConfig读取主题参数；不启用会隐藏搜索栏的uiEmbed布局。
  const url = new URL(currentSrc.value, window.location.origin);
  url.searchParams.set('nativeTheme', isDark.value ? 'dark' : 'light');
  return url.href;
});
const currentTitle = computed(
  () =>
    monitorOptions.find((item) => item.value === monitorType.value)?.label ??
    '监控面板',
);

function normalizeUrl(value: null | string, fallback: string) {
  const url = value?.trim();
  return url || fallback;
}

async function loadMonitorUrls() {
  if (loading.value) {
    return;
  }

  loading.value = true;
  errorMessage.value = '';

  try {
    const [jaegerUrl, tempoUrl] = await Promise.all([
      getConfigValueByKey(MONITOR_CONFIG_KEYS.jaeger),
      getConfigValueByKey(MONITOR_CONFIG_KEYS.tempo),
    ]);

    monitorUrls.value = {
      jaeger: normalizeUrl(jaegerUrl, DEFAULT_MONITOR_URLS.jaeger),
      tempo: normalizeUrl(tempoUrl, DEFAULT_MONITOR_URLS.tempo),
    };
  } catch (error) {
    console.warn('[InfraMonitor] load monitor urls failed:', error);
    errorMessage.value = takeErrorMessage(
      error,
      '监控地址配置读取失败，已使用默认地址',
    );
    monitorUrls.value = { ...DEFAULT_MONITOR_URLS };
  } finally {
    loading.value = false;
    initialized.value = true;
  }
}

onMounted(() => {
  void loadMonitorUrls();
});

async function refreshMonitor() {
  await loadMonitorUrls();
  frame.value?.reload();
}
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full flex-col gap-4 p-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="min-w-0">
          <h2 class="text-lg font-semibold text-foreground">监控面板</h2>
          <div class="truncate text-sm text-muted-foreground">
            {{ currentTitle }} · {{ currentSrc }}
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <ElRadioGroup v-model="monitorType">
            <ElRadioButton
              v-for="item in monitorOptions"
              :key="item.value"
              :value="item.value"
            >
              {{ item.label }}
            </ElRadioButton>
          </ElRadioGroup>

          <ElButton :loading="loading" type="primary" @click="refreshMonitor">
            <IconifyIcon icon="lucide:refresh-cw" class="mr-1 size-4" />
            刷新
          </ElButton>
          <ElButton
            tag="a"
            :href="currentSrc"
            target="_blank"
            rel="noopener noreferrer"
          >
            {{ $t('infraTools.openWindow') }}
          </ElButton>
        </div>
      </div>

      <ElAlert
        v-if="errorMessage"
        :closable="false"
        :title="errorMessage"
        show-icon
        type="warning"
      />

      <Loading :spinning="loading" :aria-busy="loading" class="min-h-0 flex-1">
        <IFrame
          ref="frame"
          v-if="initialized"
          class="h-full"
          :src="frameSrc"
          :title="currentTitle"
        />
      </Loading>
    </div>
  </Page>
</template>
