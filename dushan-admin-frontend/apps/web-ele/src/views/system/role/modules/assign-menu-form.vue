<script lang="ts" setup>
import type { SystemMenuApi } from '#/api/system/menu';
import type { SystemRoleApi } from '#/api/system/role';

import { nextTick, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { ElCheckbox, ElMessage, ElTree } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { getMenuList } from '#/api/system/menu';
import { assignRoleMenu, getRoleMenuList } from '#/api/system/role';

import { useAssignMenuFormSchema } from '../data';

defineOptions({ name: 'SystemRoleAssignMenuForm' });

const emit = defineEmits<{
  success: [];
}>();

interface MenuTreeNode extends SystemMenuApi.MenuRespVO {
  children?: MenuTreeNode[];
}

const menuTree = ref<MenuTreeNode[]>([]);
const menuTreeRef = ref<InstanceType<typeof ElTree>>();
const menuLoading = ref(false);
const isAllSelected = ref(false);
const isExpanded = ref(false);
const expandedKeys = ref<string[]>([]);

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    formItemClass: 'col-span-2',
    labelWidth: 80,
  },
  layout: 'horizontal',
  schema: useAssignMenuFormSchema(),
  showDefaultActions: false,
});

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid) return;

    modalApi.lock();
    try {
      const values = (await formApi.getValues()) as { id: string };
      const menuIds = getCheckedMenuIds();
      await assignRoleMenu(values.id, menuIds);
      await modalApi.close();
      emit('success');
      ElMessage.success($t('ui.actionMessage.operationSuccess'));
    } finally {
      modalApi.unlock();
    }
  },
  async onOpenChange(isOpen: boolean) {
    if (!isOpen) {
      resetState();
      return;
    }

    const data = modalApi.getData() as SystemRoleApi.RoleRespVO | undefined;
    if (!data?.id) return;

    modalApi.lock();
    try {
      await loadMenuTree();
      const menuIds = await getRoleMenuList(data.id);
      await formApi.setValues({
        code: data.code,
        id: data.id,
        name: data.name,
      });
      await nextTick();
      menuTreeRef.value?.setCheckedKeys(menuIds);
    } finally {
      modalApi.unlock();
    }
  },
});

async function loadMenuTree() {
  menuLoading.value = true;
  try {
    const data = await getMenuList({ paginate: false });
    menuTree.value = buildMenuTree(data);
  } finally {
    menuLoading.value = false;
  }
}

function resetState() {
  menuTree.value = [];
  isAllSelected.value = false;
  isExpanded.value = false;
  expandedKeys.value = [];
}

function getAllNodeIds(nodes: MenuTreeNode[], ids: string[] = []) {
  for (const node of nodes) {
    ids.push(node.id);
    if (node.children?.length) {
      getAllNodeIds(node.children, ids);
    }
  }
  return ids;
}

function toggleSelectAll() {
  isAllSelected.value = !isAllSelected.value;
  menuTreeRef.value?.setCheckedKeys(
    isAllSelected.value ? getAllNodeIds(menuTree.value) : [],
  );
}

function toggleExpandAll() {
  isExpanded.value = !isExpanded.value;
  expandedKeys.value = isExpanded.value ? getAllNodeIds(menuTree.value) : [];
}

function buildMenuTree(list: SystemMenuApi.MenuRespVO[]) {
  const nodeMap = new Map<string, MenuTreeNode>();
  const roots: MenuTreeNode[] = [];

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

function getCheckedMenuIds(): string[] {
  const checkedKeys = (menuTreeRef.value?.getCheckedKeys(false) ??
    []) as string[];
  const halfCheckedKeys = (menuTreeRef.value?.getHalfCheckedKeys() ??
    []) as string[];
  return [...new Set([...checkedKeys, ...halfCheckedKeys])];
}
</script>

<template>
  <Modal class="w-1/2" title="菜单权限">
    <Form class="mx-4" />

    <div class="mx-4 mb-4 grid grid-cols-[80px_1fr] gap-2">
      <div class="text-sm text-muted-foreground">菜单权限</div>
      <ElTree
        ref="menuTreeRef"
        v-loading="menuLoading"
        :data="menuTree"
        :default-expanded-keys="expandedKeys"
        :expand-on-click-node="false"
        :props="{ children: 'children', label: 'name' }"
        class="rounded border p-3"
        node-key="id"
        render-after-expand
        show-checkbox
      />
    </div>

    <template #prepend-footer>
      <div class="flex flex-auto items-center">
        <ElCheckbox :model-value="isAllSelected" @change="toggleSelectAll">
          全选
        </ElCheckbox>
        <ElCheckbox :model-value="isExpanded" @change="toggleExpandAll">
          全部展开
        </ElCheckbox>
      </div>
    </template>
  </Modal>
</template>
