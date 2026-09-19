<script lang="ts" setup>
import { Page } from '@vben/common-ui';

import { FileBrowser } from '#/components/file-browser';

defineOptions({ name: 'InfraFile' });
</script>

<template>
  <Page auto-content-height>
    <FileBrowser />
  </Page>
</template>
