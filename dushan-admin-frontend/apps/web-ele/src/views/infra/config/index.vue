<script lang="ts" setup>
import { ref } from 'vue';

import { Page } from '@vben/common-ui';

import DataGrid from './modules/data-grid.vue';
import TypeGrid from './modules/type-grid.vue';

defineOptions({ name: 'InfraConfig' });

const selectedTypeId = ref<string>();

function handleTypeSelect(typeId?: string) {
  selectedTypeId.value = typeId;
}
</script>

<template>
  <Page auto-content-height>
    <template #doc>
      <DocAlert title="配置管理" url="https://doc.iocoder.cn/infra-config/" />
    </template>

    <div class="flex h-full gap-3">
      <div class="min-w-0 flex-1">
        <TypeGrid @select="handleTypeSelect" />
      </div>
      <div class="min-w-0 flex-1">
        <DataGrid :type-id="selectedTypeId" />
      </div>
    </div>
  </Page>
</template>
