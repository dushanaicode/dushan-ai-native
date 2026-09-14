<script setup lang="ts">
import type { DocEntry } from '#/services/doc-links';

import { computed } from 'vue';

import { $t } from '@vben/locales';

import { ElAlert, ElLink } from 'element-plus';

import { buildDocUrl, useDocLinkConfig } from '#/services/doc-links';

const props = defineProps<{ entry: DocEntry }>();
const config = useDocLinkConfig();
const guideUrl = computed(
  () =>
    config.docSite &&
    buildDocUrl(config.docSite, props.entry.guidePath, {
      channel: 'doc_alert',
      content: props.entry.guidePath,
    }),
);
const deepDiveUrl = computed(
  () =>
    config.deepDiveSite &&
    props.entry.deepDivePath &&
    buildDocUrl(config.deepDiveSite, props.entry.deepDivePath, {
      channel: 'doc_alert',
      content: props.entry.deepDivePath,
    }),
);
</script>

<template>
  <ElAlert
    v-if="config.alertEnabled && guideUrl"
    type="info"
    show-icon
    :title="entry.title"
  >
    <div class="flex flex-wrap gap-4">
      <ElLink :href="guideUrl" target="_blank" rel="noopener noreferrer">
        {{ $t('utils.docLinks.guide') }}
      </ElLink>
      <ElLink
        v-if="deepDiveUrl"
        :href="deepDiveUrl"
        target="_blank"
        rel="noopener noreferrer"
        type="primary"
      >
        {{ $t('utils.docLinks.deepDive') }}
      </ElLink>
    </div>
  </ElAlert>
</template>
