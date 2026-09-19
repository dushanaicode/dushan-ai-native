import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemRoleApi } from '#/api/system/role';
import type { SwitchStatusValue } from '#/constants/status';

import { z } from '#/adapter/form';
import { DICT_TYPE } from '#/constants/dict-types';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

export function useFormSchema(): VbenFormSchema[] {
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
        placeholder: '请输入角色名称',
        showWordLimit: true,
      },
      fieldName: 'name',
      label: '角色名称',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        maxlength: 100,
        placeholder: '请输入角色标识',
        showWordLimit: true,
      },
      fieldName: 'code',
      label: '角色标识',
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
      component: 'Textarea',
      componentProps: {
        maxlength: 500,
        placeholder: '请输入角色备注',
        rows: 3,
        showWordLimit: true,
      },
      fieldName: 'remark',
      label: '角色备注',
      rules: z.string().max(500, '备注长度不能超过 500 个字符').optional(),
    },
  ];
}

export function useAssignDataPermissionFormSchema(): VbenFormSchema[] {
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
        disabled: true,
      },
      fieldName: 'name',
      label: '角色名称',
    },
    {
      component: 'Input',
      componentProps: {
        disabled: true,
      },
      fieldName: 'code',
      label: '角色标识',
    },
    {
      component: 'Select',
      componentProps: () => ({
        options: dictionary.getDictOptions(
          DICT_TYPE.SYSTEM_DATA_SCOPE,
          'number',
        ),
      }),
      fieldName: 'dataScope',
      label: '权限范围',
      rules: 'selectRequired',
    },
    {
      component: 'Input',
      dependencies: {
        show: () => false,
        triggerFields: [''],
      },
      fieldName: 'dataScopeDeptIds',
    },
  ];
}

export function useAssignMenuFormSchema(): VbenFormSchema[] {
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
      fieldName: 'name',
      label: '角色名称',
    },
    {
      component: 'Input',
      componentProps: {
        disabled: true,
      },
      fieldName: 'code',
      label: '角色标识',
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
        placeholder: '请输入角色名称',
      },
      fieldName: 'name',
      label: '角色名称',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入角色标识',
      },
      fieldName: 'code',
      label: '角色标识',
    },
    {
      component: 'Select',
      componentProps: () => ({
        clearable: true,
        options: dictionary.getDictOptions(DICT_TYPE.COMMON_STATUS, 'number'),
        placeholder: '请选择角色状态',
      }),
      fieldName: 'status',
      label: '角色状态',
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
    row: SystemRoleApi.RoleRespVO,
  ) => Promise<boolean | undefined>,
): VxeTableGridOptions<SystemRoleApi.RoleRespVO>['columns'] {
  return [
    { fixed: 'left', type: 'checkbox', width: 40 },
    {
      field: 'id',
      minWidth: 90,
      title: '角色编号',
    },
    {
      field: 'name',
      minWidth: 150,
      title: '角色名称',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.COMMON_BUILTIN_TYPE },
      },
      field: 'builtin',
      minWidth: 100,
      title: '内置类型',
    },
    {
      field: 'code',
      minWidth: 140,
      title: '角色标识',
    },
    {
      field: 'sort',
      minWidth: 100,
      title: '显示顺序',
    },
    {
      field: 'remark',
      minWidth: 180,
      title: '角色备注',
    },
    {
      align: 'center',
      cellRender: {
        name: 'CellSwitch',
        props: { change: onStatusChange },
      },
      field: 'status',
      title: '角色状态',
      width: 100,
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
