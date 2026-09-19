import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemDeptApi } from '#/api/system/dept';
import type { SwitchStatusValue } from '#/constants/status';

import { z } from '#/adapter/form';
import { getSimpleDeptList } from '#/api/system/dept';
import { DICT_TYPE } from '#/constants/dict-types';
import { SwitchStatus } from '#/constants/status';
import { useDictionary } from '#/services/dictionary/context';
import { createUserSelectPorts } from '#/services/user-select/ports';

interface DeptTreeNode extends SystemDeptApi.DeptSimpleRespVO {
  children?: DeptTreeNode[];
}

function buildDeptTree(
  list: SystemDeptApi.DeptSimpleRespVO[],
  excludeId?: string,
): DeptTreeNode[] {
  const nodeMap = new Map<string, DeptTreeNode>();
  const roots: DeptTreeNode[] = [];

  for (const item of list) {
    if (item.id === excludeId) continue;
    nodeMap.set(item.id, { ...item });
  }

  for (const item of list) {
    if (item.id === excludeId) continue;

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

export function useFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
    {
      component: 'Input',
      dependencies: {
        show: () => false,
        triggerFields: [''],
      },
      fieldName: 'id',
    },
    {
      component: 'ApiTreeSelect',
      componentProps: (ctx) => {
        return {
          api: async () => {
            const data = await getSimpleDeptList();
            return [
              {
                children: buildDeptTree(data, ctx.rootValues?.id),
                id: '0',
                name: '顶级部门',
              },
            ];
          },
          checkStrictly: true,
          childrenField: 'children',
          clearable: true,
          labelField: 'name',
          nodeKey: 'id',
          placeholder: '请选择上级部门',
          props: { children: 'children', label: 'name' },
          treeDefaultExpandAll: true,
          valueField: 'id',
        };
      },
      dependencies: {
        triggerFields: ['id'],
      },
      fieldName: 'parentId',
      label: '上级部门',
      rules: 'selectRequired',
    },
    {
      component: 'Input',
      componentProps: {
        maxlength: 30,
        placeholder: '请输入部门名称',
        showWordLimit: true,
      },
      fieldName: 'name',
      label: '部门名称',
      rules: 'required',
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: 0,
        placeholder: '请输入显示顺序',
      },
      fieldName: 'sort',
      label: '显示顺序',
      rules: 'required',
    },
    {
      component: 'UserSelectFormField',
      componentProps: {
        placeholder: '请选择负责人',
        ports: createUserSelectPorts(),
        showDeptFilter: true,
      },
      fieldName: 'leaderUserId',
      label: '负责人',
    },
    {
      component: 'Input',
      componentProps: {
        maxlength: 11,
        placeholder: '请输入联系电话',
        showWordLimit: true,
      },
      fieldName: 'phone',
      label: '联系电话',
      rules: 'mobile',
    },
    {
      component: 'Input',
      componentProps: {
        maxlength: 50,
        placeholder: '请输入邮箱',
        showWordLimit: true,
      },
      fieldName: 'email',
      label: '邮箱',
      rules: z
        .union([z.string().email('请输入正确的邮箱地址'), z.literal('')])
        .optional(),
    },
    {
      component: 'RadioGroup',
      componentProps: () => ({
        isButton: true,
        options: dictionary.getDictOptions(DICT_TYPE.COMMON_STATUS, 'number'),
      }),
      fieldName: 'status',
      label: '状态',
      rules: z.number().default(SwitchStatus.ENABLED),
    },
  ];
}

export function useGridFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入部门名称',
      },
      fieldName: 'name',
      label: '部门名称',
    },
    {
      component: 'Select',
      componentProps: () => ({
        clearable: true,
        options: dictionary.getDictOptions(DICT_TYPE.COMMON_STATUS, 'number'),
        placeholder: '请选择状态',
      }),
      fieldName: 'status',
      label: '状态',
    },
  ];
}

export function useGridColumns(
  getLeaderName?: (userId: string) => string | undefined,
  onStatusChange?: (
    newStatus: SwitchStatusValue,
    row: any,
  ) => Promise<boolean | undefined>,
): VxeTableGridOptions<SystemDeptApi.DeptRespVO>['columns'] {
  return [
    { fixed: 'left', type: 'checkbox', width: 40 },
    {
      align: 'left',
      field: 'name',
      fixed: 'left',
      minWidth: 220,
      title: '部门名称',
      treeNode: true,
    },
    {
      field: 'leaderUserId',
      formatter: ({ cellValue }) => getLeaderName?.(cellValue) || '-',
      minWidth: 140,
      title: '负责人',
    },
    {
      field: 'sort',
      minWidth: 100,
      title: '显示顺序',
    },
    {
      align: 'center',
      cellRender: {
        name: 'CellSwitch',
        props: { change: onStatusChange },
      },
      field: 'status',
      title: '状态',
      width: 90,
    },
    {
      field: 'createTime',
      formatter: 'formatDateTime',
      minWidth: 180,
      title: '创建时间',
    },
    {
      align: 'center',
      fixed: 'right',
      minWidth: 220,
      slots: { default: 'actions' },
      title: '操作',
    },
  ];
}
