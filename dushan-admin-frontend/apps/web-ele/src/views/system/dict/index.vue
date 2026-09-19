<script lang="ts" setup>
import { ref } from 'vue';

import { Page } from '@vben/common-ui';

import DataGrid from './modules/data-grid.vue';
import TypeGrid from './modules/type-grid.vue';

defineOptions({ name: 'SystemDict' });

const selectedDictType = ref<string>();

function handleDictTypeSelect(dictType: string) {
  selectedDictType.value = dictType;
}
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full gap-3">
      <div class="min-w-0 flex-1">
        <TypeGrid @select="handleDictTypeSelect" />
      </div>
      <div class="min-w-0 flex-1">
        <DataGrid :dict-type="selectedDictType" />
      </div>
    </div>
  </Page>
</template>
