import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SwitchStatusValue } from '#/constants/status';

import { z } from '#/adapter/form';
import { DICT_TYPE } from '#/constants/dict-types';
import { SwitchStatus } from '#/constants/status';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

export function usePostFormSchema(): VbenFormSchema[] {
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
        placeholder: '请输入岗位名称',
      },
      fieldName: 'name',
      label: '岗位名称',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入岗位编码',
      },
      fieldName: 'code',
      label: '岗位编码',
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
      component: 'RadioGroup',
      componentProps: () => ({
        isButton: true,
        options: dictionary.getDictOptions(DICT_TYPE.COMMON_STATUS, 'number'),
      }),
      fieldName: 'status',
      label: '状态',
      rules: z.number().default(SwitchStatus.ENABLED),
    },
    {
      component: 'Textarea',
      componentProps: {
        maxlength: 255,
        placeholder: '请输入备注',
        showWordLimit: true,
      },
      fieldName: 'remark',
      label: '备注',
    },
  ];
}

export function usePostGridFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入岗位名称',
      },
      fieldName: 'name',
      label: '岗位名称',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入岗位编码',
      },
      fieldName: 'code',
      label: '岗位编码',
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

export function usePostGridColumns(
  onStatusChange?: (
    newStatus: SwitchStatusValue,
    row: any,
  ) => Promise<boolean | undefined>,
): VxeTableGridOptions['columns'] {
  return [
    { fixed: 'left', type: 'checkbox', width: 40 },
    {
      field: 'id',
      minWidth: 100,
      title: '岗位序号',
    },
    {
      field: 'name',
      minWidth: 160,
      title: '岗位名称',
    },
    {
      field: 'code',
      minWidth: 160,
      title: '岗位编码',
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
      field: 'remark',
      minWidth: 180,
      title: '备注',
    },
    {
      field: 'createTime',
      formatter: 'formatDateTime',
      minWidth: 180,
      title: '创建时间',
    },
    {
      align: 'center',
      field: 'operation',
      fixed: 'right',
      minWidth: 120,
      slots: { default: 'actions' },
      title: '操作',
    },
  ];
}
