<script lang="ts" setup>
import type { SystemDeptApi } from '#/api/system/dept';

import { computed, onMounted, ref, watch } from 'vue';

import { IconifyIcon } from '@vben/icons';

import { ElButton, ElCard, ElInput, ElTree } from 'element-plus';

import { getSimpleDeptList } from '#/api/system/dept';

interface DeptTreeNode extends SystemDeptApi.DeptSimpleRespVO {
  children?: DeptTreeNode[];
}

const emit = defineEmits<{
  select: [dept?: SystemDeptApi.DeptSimpleRespVO];
}>();

const filterText = ref('');
const treeRef = ref<InstanceType<typeof ElTree>>();
const loading = ref(false);
const deptList = ref<DeptTreeNode[]>([]);

const treeProps = {
  children: 'children',
  label: 'name',
};

const emptyText = computed(() => (loading.value ? '加载中...' : '暂无部门'));

function buildDeptTree(list: SystemDeptApi.DeptSimpleRespVO[]): DeptTreeNode[] {
  const nodeMap = new Map<string, DeptTreeNode>();
  const roots: DeptTreeNode[] = [];

  for (const item of list) {
    nodeMap.set(item.id, { ...item });
  }

  for (const item of list) {
    const node = nodeMap.get(item.id);
    if (!node) continue;

    const parentId = item.parentId ?? '0';
    const parentNode = nodeMap.get(parentId);
    if (parentId !== '0' && parentNode) {
      parentNode.children ||= [];
      parentNode.children.push(node);
    } else {
      roots.push(node);
    }
  }

  return roots;
}

function filterNode(value: string, data: { name?: string }) {
  if (!value) return true;
  return data.name?.includes(value) ?? false;
}

async function loadDeptTree() {
  loading.value = true;
  try {
    deptList.value = buildDeptTree(await getSimpleDeptList());
  } finally {
    loading.value = false;
  }
}

function onNodeClick(data: DeptTreeNode) {
  emit('select', data);
}

function onSelectAll() {
  treeRef.value?.setCurrentKey(undefined);
  emit('select');
}

onMounted(loadDeptTree);

watch(filterText, (value) => {
  treeRef.value?.filter(value);
});
</script>

<template>
  <ElCard class="h-full" shadow="never">
    <template #header>
      <div class="flex items-center justify-between">
        <span class="text-base font-medium">部门</span>
        <ElButton link type="primary" @click="onSelectAll">全部</ElButton>
      </div>
    </template>

    <ElInput
      v-model="filterText"
      class="mb-3"
      clearable
      placeholder="请输入部门名称"
    >
      <template #prefix>
        <IconifyIcon class="size-4" icon="lucide:search" />
      </template>
    </ElInput>

    <ElTree
      ref="treeRef"
      :data="deptList"
      :empty-text="emptyText"
      :expand-on-click-node="false"
      :filter-node-method="filterNode"
      :props="treeProps"
      default-expand-all
      node-key="id"
      @node-click="onNodeClick"
    />
  </ElCard>
</template>
