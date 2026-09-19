import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemDeptApi } from '#/api/system/dept';
import type { SystemUserApi } from '#/api/system/user';
import type { SwitchStatusValue } from '#/constants/status';

import { z } from '#/adapter/form';
import { getSimpleDeptList } from '#/api/system/dept';
import { getSimplePostList } from '#/api/system/post';
import { getSimpleRoleList } from '#/api/system/role';
import { DICT_TYPE } from '#/constants/dict-types';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

interface DeptTreeNode extends SystemDeptApi.DeptSimpleRespVO {
  children?: DeptTreeNode[];
}

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
      component: 'Input',
      componentProps: {
        maxlength: 30,
        placeholder: '请输入用户账号',
        showWordLimit: true,
      },
      dependencies: {
        disabled: (values) => !!values.id,
        triggerFields: ['id'],
      },
      fieldName: 'username',
      label: '用户账号',
      rules: 'required',
    },
    {
      component: 'VbenInputPassword',
      componentProps: {
        maxlength: 16,
        passwordStrength: true,
        placeholder: '请输入用户密码',
        showWordLimit: true,
      },
      dependencies: {
        show: (values) => !values.id,
        triggerFields: ['id'],
      },
      fieldName: 'password',
      label: '用户密码',
      rules: z
        .string()
        .min(4, '密码长度不能少于 4 位')
        .max(16, '密码长度不能超过 16 位'),
    },
    {
      component: 'Input',
      componentProps: {
        maxlength: 30,
        placeholder: '请输入用户昵称',
        showWordLimit: true,
      },
      fieldName: 'nickname',
      label: '用户昵称',
      rules: 'required',
    },
    {
      component: 'ApiTreeSelect',
      componentProps: {
        api: async () => {
          const data = await getSimpleDeptList();
          return buildDeptTree(data);
        },
        checkStrictly: true,
        childrenField: 'children',
        clearable: true,
        labelField: 'name',
        nodeKey: 'id',
        placeholder: '请选择归属部门',
        props: { children: 'children', label: 'name' },
        treeDefaultExpandAll: true,
        valueField: 'id',
      },
      fieldName: 'deptId',
      label: '归属部门',
    },
    {
      component: 'ApiSelect',
      componentProps: {
        api: getSimplePostList,
        clearable: true,
        labelField: 'name',
        multiple: true,
        placeholder: '请选择岗位',
        valueField: 'id',
      },
      fieldName: 'postIds',
      label: '岗位',
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
      component: 'Input',
      componentProps: {
        maxlength: 11,
        placeholder: '请输入手机号',
        showWordLimit: true,
      },
      fieldName: 'mobile',
      label: '手机号',
      rules: 'mobile',
    },
    {
      component: 'RadioGroup',
      componentProps: () => ({
        isButton: true,
        options: dictionary.getDictOptions(DICT_TYPE.SYSTEM_USER_SEX, 'number'),
      }),
      fieldName: 'sex',
      label: '用户性别',
    },
    {
      component: 'Textarea',
      componentProps: {
        maxlength: 200,
        placeholder: '请输入备注',
        rows: 3,
        showWordLimit: true,
      },
      fieldName: 'remark',
      label: '备注',
    },
  ];
}

export function useResetPasswordFormSchema(): VbenFormSchema[] {
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
      component: 'Input',
      componentProps: {
        disabled: true,
      },
      fieldName: 'username',
      label: '用户账号',
    },
    {
      component: 'VbenInputPassword',
      componentProps: {
        maxlength: 16,
        passwordStrength: true,
        placeholder: '请输入新密码',
        showWordLimit: true,
      },
      fieldName: 'password',
      label: '新密码',
      rules: z
        .string()
        .min(4, '密码长度不能少于 4 位')
        .max(16, '密码长度不能超过 16 位'),
    },
  ];
}

export function useAssignRoleFormSchema(): VbenFormSchema[] {
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
      component: 'Input',
      componentProps: {
        disabled: true,
      },
      fieldName: 'username',
      label: '用户账号',
    },
    {
      component: 'Input',
      componentProps: {
        disabled: true,
      },
      fieldName: 'nickname',
      label: '用户昵称',
    },
    {
      component: 'ApiSelect',
      componentProps: {
        api: getSimpleRoleList,
        clearable: true,
        labelField: 'name',
        multiple: true,
        placeholder: '请选择角色',
        valueField: 'id',
      },
      fieldName: 'roleIds',
      label: '角色',
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
        placeholder: '请输入用户账号',
      },
      fieldName: 'username',
      label: '用户账号',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入手机号',
      },
      fieldName: 'mobile',
      label: '手机号',
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
    {
      component: 'RangePicker',
      componentProps: {
        ...getRangePickerDefaultProps(),
        clearable: true,
      },
      fieldName: 'createTime',
      label: '创建时间',
    },
  ];
}

export function useGridColumns(
  onStatusChange?: (
    newStatus: SwitchStatusValue,
    row: SystemUserApi.UserRespVO,
  ) => Promise<boolean | undefined>,
): VxeTableGridOptions<SystemUserApi.UserRespVO>['columns'] {
  return [
    { fixed: 'left', type: 'checkbox', width: 40 },
    {
      field: 'id',
      minWidth: 80,
      title: '用户编号',
    },
    {
      field: 'username',
      minWidth: 140,
      title: '用户账号',
    },
    {
      field: 'nickname',
      minWidth: 140,
      title: '用户昵称',
    },
    {
      field: 'deptName',
      minWidth: 140,
      title: '部门',
    },
    {
      field: 'mobile',
      minWidth: 140,
      title: '手机号',
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
      minWidth: 240,
      slots: { default: 'actions' },
      title: '操作',
    },
  ];
}
