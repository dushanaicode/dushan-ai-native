<script setup lang="ts">
import { useRoute } from 'vue-router';

import { ElLink } from 'element-plus';

const route = useRoute();
</script>

<template>
  <div class="p-6">
    <ElLink :href="route.meta.link" target="_blank" rel="noopener noreferrer">
      {{ route.meta.title }}
    </ElLink>
  </div>
</template>
