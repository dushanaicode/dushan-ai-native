<script lang="ts" setup>
import type { SystemMenuApi } from '#/api/system/menu';
import type { SystemTenantPackageApi } from '#/api/system/tenant/package';

import { computed, ref } from 'vue';

import { Tree, useVbenModal } from '@vben/common-ui';

import { ElMessage } from 'element-plus';

import { useVbenForm } from '#/adapter/form';
import { getMenuSimpleList } from '#/api/system/menu';
import {
  createTenantPackage,
  getTenantPackage,
  updateTenantPackage,
} from '#/api/system/tenant/package';
import { $t } from '#/locales';

import { useFormSchema } from '../data';

defineOptions({ name: 'SystemTenantPackageForm' });

const emit = defineEmits(['success']);

interface TenantPackageFormValues
  extends SystemTenantPackageApi.TenantPackageSaveReqVO {
  aiBillingMode?: number;
  aiDailyTokenLimit?: number;
  aiEnabled?: boolean;
  aiMonthlyAmountLimit?: number;
  aiMonthlyTokenLimit?: number;
  dividerAiQuota?: string;
}

interface MenuTreeNode extends SystemMenuApi.MenuSimpleRespVO {
  children?: MenuTreeNode[];
}

const formData = ref<SystemTenantPackageApi.TenantPackageRespVO>();
const menuTree = ref<MenuTreeNode[]>([]);

const title = computed(() =>
  formData.value?.id
    ? $t('ui.actionTitle.edit', ['租户套餐'])
    : $t('ui.actionTitle.create', ['租户套餐']),
);

const [Form, formApi] = useVbenForm({
  commonConfig: {
    componentProps: {
      class: 'w-full',
    },
    formItemClass: 'col-span-2',
    labelWidth: 110,
  },
  layout: 'horizontal',
  schema: useFormSchema(),
  showDefaultActions: false,
});

function flattenQuotaConfig(
  quotaConfig?: SystemTenantPackageApi.TenantPackageQuotaConfigVO,
) {
  const ai = quotaConfig?.ai;
  return {
    aiBillingMode: ai?.billingMode ?? 1,
    aiDailyTokenLimit: ai?.dailyTokenLimit ?? -1,
    aiEnabled: ai?.enabled ?? false,
    aiMonthlyAmountLimit: ai?.monthlyAmountLimit ?? -1,
    aiMonthlyTokenLimit: ai?.monthlyTokenLimit ?? -1,
  };
}

function buildQuotaConfig(values: TenantPackageFormValues) {
  return {
    ai: {
      billingMode: values.aiBillingMode ?? 1,
      dailyTokenLimit: values.aiDailyTokenLimit ?? -1,
      enabled: values.aiEnabled ?? false,
      monthlyAmountLimit: values.aiMonthlyAmountLimit ?? -1,
      monthlyTokenLimit: values.aiMonthlyTokenLimit ?? -1,
    },
  };
}

function toStringIds(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.map(String);
}

function normalizeFormValues(
  values: TenantPackageFormValues,
): SystemTenantPackageApi.TenantPackageSaveReqVO {
  return {
    id: values.id,
    menuIds: toStringIds(values.menuIds),
    name: values.name,
    quotaConfig: buildQuotaConfig(values),
    remark: values.remark || undefined,
    status: values.status,
  };
}

async function loadMenuTree() {
  const list = await getMenuSimpleList();
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

  menuTree.value = roots;
}

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid) {
      return;
    }

    modalApi.lock();
    const values = (await formApi.getValues()) as TenantPackageFormValues;
    const data = normalizeFormValues(values);

    try {
      await (formData.value?.id
        ? updateTenantPackage(data)
        : createTenantPackage(data));
      await modalApi.close();
      emit('success');
      ElMessage.success($t('ui.actionMessage.operationSuccess'));
    } finally {
      modalApi.unlock();
    }
  },
  async onOpenChange(isOpen: boolean) {
    if (!isOpen) {
      formData.value = undefined;
      return;
    }

    modalApi.lock();
    try {
      await loadMenuTree();
      const data = modalApi.getData() as
        | SystemTenantPackageApi.TenantPackageRespVO
        | undefined;

      if (!data?.id) {
        await formApi.setValues({
          menuIds: [],
          ...flattenQuotaConfig(),
        });
        return;
      }

      formData.value = await getTenantPackage(data.id);
      await formApi.setValues({
        ...formData.value,
        ...flattenQuotaConfig(formData.value.quotaConfig),
      });
    } finally {
      modalApi.unlock();
    }
  },
});
</script>

<template>
  <Modal class="w-1/2" :title="title">
    <Form class="mx-4">
      <template #menuIds="slotProps">
        <Tree
          v-bind="slotProps"
          bordered
          children-field="children"
          class="max-h-96 overflow-y-auto rounded border p-2"
          :default-expanded-level="2"
          label-field="name"
          multiple
          select-all-label="菜单权限"
          :tree-data="menuTree"
          value-field="id"
        />
      </template>
    </Form>
  </Modal>
</template>
