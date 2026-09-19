<script lang="ts" setup>
import type { RedisCacheTreeNode } from '../data';

import type { InfraRedisCacheApi } from '#/api/infra/redis-cache';

import { IconifyIcon } from '@vben/icons';

import {
  ElBadge,
  ElButton,
  ElCard,
  ElEmpty,
  ElInput,
  ElOption,
  ElSelect,
  ElTree,
} from 'element-plus';

defineOptions({ name: 'InfraRedisCacheKeyTreePanel' });

defineProps<{
  dbList: InfraRedisCacheApi.CacheDbInfoRespVO[];
  loadingDb: boolean;
  loadingKeys: boolean;
  rawKeysCount: number;
  treeData: RedisCacheTreeNode[];
}>();

const emit = defineEmits<{
  dbChange: [];
  nodeClick: [node: RedisCacheTreeNode];
  refresh: [];
  search: [];
}>();

const selectedDb = defineModel<string>('selectedDb', { required: true });
const searchPattern = defineModel<string>('searchPattern', { required: true });

const treeProps = {
  children: 'children',
  isLeaf: 'isLeaf',
  label: 'label',
};
</script>

<template>
  <ElCard
    class="h-full overflow-hidden"
    :body-style="{
      padding: 0,
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
    }"
  >
    <div
      class="flex items-center gap-2 border-b border-border bg-muted/40 px-3 py-3"
    >
      <ElSelect
        v-model="selectedDb"
        :loading="loadingDb"
        class="min-w-0 flex-1"
        placeholder="选择 DB"
        @change="emit('dbChange')"
      >
        <ElOption
          v-for="db in dbList"
          :key="db.name"
          :label="db.label"
          :value="db.name"
        >
          <div class="flex items-center justify-between gap-3">
            <span class="truncate">{{ db.label }}</span>
            <ElBadge :max="9999" :value="db.keyCount" />
          </div>
        </ElOption>
      </ElSelect>

      <ElButton :loading="loadingDb || loadingKeys" @click="emit('refresh')">
        <IconifyIcon icon="lucide:refresh-cw" class="mr-1 size-4" />
        刷新
      </ElButton>
    </div>

    <div class="border-b border-border px-3 py-2">
      <ElInput
        v-model="searchPattern"
        clearable
        placeholder="搜索 key，支持 * 通配符"
        @keyup.enter="emit('search')"
      >
        <template #prefix>
          <IconifyIcon icon="lucide:search" class="size-4" />
        </template>
        <template #suffix>
          <span class="whitespace-nowrap text-xs text-muted-foreground">
            {{ rawKeysCount }} keys
          </span>
        </template>
      </ElInput>
    </div>

    <div v-loading="loadingKeys" class="min-h-0 flex-1 overflow-auto px-1 py-2">
      <ElTree
        v-if="treeData.length > 0"
        :data="treeData"
        :props="treeProps"
        highlight-current
        node-key="id"
        @node-click="(node: RedisCacheTreeNode) => emit('nodeClick', node)"
      >
        <template #default="{ node, data }">
          <span class="inline-flex min-w-0 items-center gap-1 text-sm">
            <IconifyIcon
              :icon="data.isLeaf ? 'lucide:key-round' : 'lucide:folder'"
              class="size-4 flex-shrink-0 text-muted-foreground"
            />
            <span class="max-w-[220px] truncate">{{ node.label }}</span>
            <span
              v-if="!data.isLeaf && data.count"
              class="text-xs text-muted-foreground"
            >
              ({{ data.count }})
            </span>
          </span>
        </template>
      </ElTree>
      <ElEmpty v-else description="暂无 Key" />
    </div>
  </ElCard>
</template>
