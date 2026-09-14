<script setup lang="ts">
import { computed } from 'vue';

import { $t } from '@vben/locales';

import {
  buildDocUrl,
  projectLinks,
  useDocLinkConfig,
} from '#/services/doc-links';

const config = useDocLinkConfig();
const links = computed(() => [
  ...(config.docSite
    ? [
        {
          href: buildDocUrl(config.docSite, '', {
            channel: 'login',
            content: 'home',
          }),
          text: $t('utils.docLinks.docs'),
        },
      ]
    : []),
  ...(config.deepDiveSite
    ? [
        {
          href: buildDocUrl(config.deepDiveSite, '', {
            channel: 'login',
            content: 'home',
          }),
          text: $t('utils.docLinks.deepDive'),
        },
      ]
    : []),
  { href: projectLinks.github, text: 'GitHub' },
  { href: projectLinks.mirror, text: 'Gitee' },
]);
</script>

<template>
  <nav class="flex flex-wrap justify-center gap-4">
    <a
      v-for="link in links"
      :key="link.href"
      :href="link.href"
      class="hover:text-primary"
      rel="noopener noreferrer"
      target="_blank"
    >
      {{ link.text }}
    </a>
  </nav>
</template>
