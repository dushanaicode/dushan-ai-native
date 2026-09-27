<script setup lang="ts">
import { computed, ref } from 'vue';

import { Page } from '@vben/common-ui';

import { ElButton, ElRadioButton, ElRadioGroup } from 'element-plus';

import { IFrame } from '#/components';
import { $t } from '#/locales';

defineOptions({ name: 'InfraDocs' });

const documentType = ref<'docs' | 'redoc'>('docs');
const frame = ref<InstanceType<typeof IFrame>>();
const source = computed(() => `/${documentType.value}`);
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full min-h-0 flex-col gap-4 p-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <h2 class="text-lg font-semibold">{{ $t('infraTools.docsTitle') }}</h2>
        <div class="flex flex-wrap items-center gap-2">
          <ElRadioGroup v-model="documentType">
            <ElRadioButton value="docs">Swagger UI</ElRadioButton>
            <ElRadioButton value="redoc">ReDoc</ElRadioButton>
          </ElRadioGroup>
          <ElButton @click="frame?.reload()">
            {{ $t('infraTools.refresh') }}
          </ElButton>
          <ElButton
            tag="a"
            :href="source"
            target="_blank"
            rel="noopener noreferrer"
          >
            {{ $t('infraTools.openWindow') }}
          </ElButton>
        </div>
      </div>
      <IFrame
        ref="frame"
        :src="source"
        :title="$t('infraTools.docsTitle')"
        class="min-h-0 flex-1"
      />
    </div>
  </Page>
</template>
