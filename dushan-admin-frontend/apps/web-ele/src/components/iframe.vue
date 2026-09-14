<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import { $t } from '@vben/locales';

import { ElButton, ElEmpty } from 'element-plus';

const props = withDefaults(
  defineProps<{
    src?: string;
    title?: string;
    width?: number | string;
    height?: number | string;
    showLoading?: boolean;
    loadingText?: string;
    errorText?: string;
    emptyText?: string;
    sandbox?: string;
    allow?: string;
    allowFullscreen?: boolean;
    referrerPolicy?: ReferrerPolicy;
  }>(),
  {
    src: '',
    title: 'iframe',
    width: '100%',
    height: '100%',
    showLoading: true,
    referrerPolicy: 'no-referrer',
    loadingText: undefined,
    errorText: undefined,
    emptyText: undefined,
    sandbox: undefined,
    allow: undefined,
  },
);
const emit = defineEmits<{
  load: [event: Event];
  error: [event: Event];
  reload: [];
}>();
const loading = ref(false);
const failed = ref(false);
const revision = ref(0);
const href = computed(() => {
  if (!props.src) return '';
  const url = new URL(props.src, window.location.origin);
  if (
    !['http:', 'https:'].includes(url.protocol) ||
    url.username ||
    url.password
  )
    throw new TypeError('内嵌地址必须是HTTP(S) URL');
  return url.href;
});
watch(
  href,
  () => {
    loading.value = !!href.value;
    failed.value = false;
  },
  { immediate: true },
);
function reload() {
  revision.value += 1;
  loading.value = true;
  failed.value = false;
  emit('reload');
}
function loaded(event: Event) {
  loading.value = false;
  failed.value = false;
  emit('load', event);
}
function error(event: Event) {
  loading.value = false;
  failed.value = true;
  emit('error', event);
}
defineExpose({ reload });
</script>

<template>
  <div
    class="relative min-h-0 overflow-hidden rounded-md border"
    :style="{
      width: typeof width === 'number' ? `${width}px` : width,
      height: typeof height === 'number' ? `${height}px` : height,
    }"
  >
    <ElEmpty
      v-if="!href"
      :description="emptyText ?? $t('utils.iframe.empty')"
    />
    <template v-else>
      <iframe
        :key="`${href}-${revision}`"
        :src="href"
        :title="title"
        :sandbox="sandbox"
        :allow="allow"
        :allowfullscreen="allowFullscreen"
        :referrerpolicy="referrerPolicy"
        class="h-full w-full border-0"
        @load="loaded"
        @error="error"
      ></iframe>
      <div
        v-if="showLoading && loading"
        class="bg-background absolute inset-0 flex items-center justify-center"
        role="status"
      >
        {{ loadingText ?? $t('utils.iframe.loading') }}
      </div>
      <ElEmpty
        v-if="failed"
        :description="errorText ?? $t('utils.iframe.failed')"
        class="bg-background absolute inset-0"
      >
        <ElButton @click="reload">
          <span>{{ $t('utils.iframe.reload') }}</span>
        </ElButton>
      </ElEmpty>
    </template>
  </div>
</template>
