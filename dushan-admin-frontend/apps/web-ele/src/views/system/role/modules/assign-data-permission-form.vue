<script lang="ts" setup>
import type { SystemDeptApi } from '#/api/system/dept';
import type { SystemRoleApi } from '#/api/system/role';

import { computed, nextTick, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';
import { isEmpty } from '@vben/utils';

import { ElCheckbox, ElMessage, ElTree } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { getSimpleDeptList } from '#/api/system/dept';
import { assignRoleDataScope, getRole } from '#/api/system/role';
import { DataScope } from '#/constants/data-scope';

import { useAssignDataPermissionFormSchema } from '../data';

defineOptions({ name: 'SystemRoleAssignDataPermissionForm' });

const emit = defineEmits<{
  success: [];
}>();

interface DeptTreeNode extends SystemDeptApi.DeptSimpleRespVO {
  children?: DeptTreeNode[];
}

const deptTree = ref<DeptTreeNode[]>([]);
const deptTreeRef = ref<InstanceType<typeof ElTree>>();
const deptLoading = ref(false);
const isAllSelected = ref(false);
const isExpanded = ref(false);
const linkParentChild = ref(true);
const expandedKeys = ref<string[]>([]);
const dataScopeValue = ref<number>();

const showDeptTree = computed(() => {
  return dataScopeValue.value === DataScope.DEPT_CUSTOM;
});

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    formItemClass: 'col-span-2',
    labelWidth: 80,
  },
  handleValuesChange(values, fieldsChanged) {
    if (fieldsChanged.includes('dataScope')) {
      dataScopeValue.value = values.dataScope;
    }
  },
  layout: 'horizontal',
  schema: useAssignDataPermissionFormSchema(),
  showDefaultActions: false,
});

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid) return;

    const values = (await formApi.getValues()) as {
      dataScope: number;
      id: string;
    };
    const dataScopeDeptIds = getCheckedDeptIds();

    if (
      values.dataScope === DataScope.DEPT_CUSTOM &&
      isEmpty(dataScopeDeptIds)
    ) {
      ElMessage.warning('请选择部门范围');
      return;
    }

    modalApi.lock();
    try {
      await assignRoleDataScope(
        values.id,
        values.dataScope,
        values.dataScope === DataScope.DEPT_CUSTOM
          ? dataScopeDeptIds
          : undefined,
      );
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
      await loadDeptTree();
      expandAll();
      const detail = await getRole(data.id);
      dataScopeValue.value = detail.dataScope;
      await formApi.setValues(detail);
      await nextTick();
      deptTreeRef.value?.setCheckedKeys(detail.dataScopeDeptIds ?? []);
    } finally {
      modalApi.unlock();
    }
  },
});

async function loadDeptTree() {
  deptLoading.value = true;
  try {
    const data = await getSimpleDeptList();
    deptTree.value = buildDeptTree(data);
  } finally {
    deptLoading.value = false;
  }
}

function resetState() {
  deptTree.value = [];
  isAllSelected.value = false;
  isExpanded.value = false;
  linkParentChild.value = true;
  expandedKeys.value = [];
  dataScopeValue.value = undefined;
}

function getAllNodeIds(nodes: DeptTreeNode[], ids: string[] = []) {
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
  deptTreeRef.value?.setCheckedKeys(
    isAllSelected.value ? getAllNodeIds(deptTree.value) : [],
  );
}

function expandAll() {
  isExpanded.value = true;
  expandedKeys.value = getAllNodeIds(deptTree.value);
}

function toggleExpandAll() {
  isExpanded.value = !isExpanded.value;
  expandedKeys.value = isExpanded.value ? getAllNodeIds(deptTree.value) : [];
}

function toggleLinkParentChild() {
  linkParentChild.value = !linkParentChild.value;
}

function buildDeptTree(list: SystemDeptApi.DeptSimpleRespVO[]) {
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

function getCheckedDeptIds(): string[] {
  return (deptTreeRef.value?.getCheckedKeys(false) ?? []) as string[];
}
</script>

<template>
  <Modal class="w-1/2" title="数据权限">
    <Form class="mx-4" />

    <div v-if="showDeptTree" class="mx-4 mb-4 grid grid-cols-[80px_1fr] gap-2">
      <div class="text-sm text-muted-foreground">部门范围</div>
      <ElTree
        ref="deptTreeRef"
        v-loading="deptLoading"
        :check-strictly="!linkParentChild"
        :data="deptTree"
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
      <div v-if="showDeptTree" class="flex flex-auto items-center">
        <ElCheckbox :model-value="isAllSelected" @change="toggleSelectAll">
          全选
        </ElCheckbox>
        <ElCheckbox :model-value="isExpanded" @change="toggleExpandAll">
          全部展开
        </ElCheckbox>
        <ElCheckbox
          :model-value="linkParentChild"
          @change="toggleLinkParentChild"
        >
          父子联动
        </ElCheckbox>
      </div>
    </template>
  </Modal>
</template>
