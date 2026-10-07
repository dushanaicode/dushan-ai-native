<script setup lang="ts">
import { useUserStore } from '@vben/stores';

import { ElTag, ElTooltip } from 'element-plus';

import { $t } from '#/locales';

const userStore = useUserStore();
</script>

<template>
  <ElTooltip
    v-if="userStore.userRoles.includes('readonly')"
    :content="$t('readonlyDemo.description')"
    placement="bottom"
  >
    <ElTag class="mx-2 shrink-0" tabindex="0" type="warning">
      {{ $t('readonlyDemo.label') }}
    </ElTag>
  </ElTooltip>
</template>
