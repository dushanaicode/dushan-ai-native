import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SwitchStatusValue } from '#/constants/status';

import { z } from '#/adapter/form';
import { getSimpleDictTypeList } from '#/api/system/dict/type';
import { DICT_TYPE } from '#/constants/dict-types';
import { SwitchStatus } from '#/constants/status';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

// 与后端 DictDataRespVO.colorType 枚举值一致
const colorOptions = [
  { label: '无', value: '' },
  { label: '主要', value: 'primary' },
  { label: '成功', value: 'success' },
  { label: '信息', value: 'info' },
  { label: '警告', value: 'warning' },
  { label: '危险', value: 'danger' },
  { label: '默认', value: 'default' },
];

export function useTypeFormSchema(): VbenFormSchema[] {
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
        placeholder: '请输入字典名称',
      },
      fieldName: 'name',
      label: '字典名称',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: (ctx) => {
        return {
          disabled: !!ctx.rootValues?.id,
          placeholder: '请输入字典类型',
        };
      },
      dependencies: {
        triggerFields: [''],
      },
      fieldName: 'type',
      label: '字典类型',
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
        placeholder: '请输入备注',
      },
      fieldName: 'remark',
      label: '备注',
    },
  ];
}

export function useTypeGridFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入字典名称',
      },
      fieldName: 'name',
      label: '字典名称',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入字典类型',
      },
      fieldName: 'type',
      label: '字典类型',
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

export function useTypeGridColumns(
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
      title: '字典编号',
    },
    {
      field: 'name',
      minWidth: 200,
      title: '字典名称',
    },
    {
      field: 'type',
      minWidth: 220,
      title: '字典类型',
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

export function useDataFormSchema(): VbenFormSchema[] {
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
      component: 'ApiSelect',
      componentProps: (ctx) => {
        return {
          api: getSimpleDictTypeList,
          disabled: !!ctx.rootValues?.id,
          labelField: 'name',
          placeholder: '请输入字典类型',
          valueField: 'type',
        };
      },
      dependencies: {
        triggerFields: [''],
      },
      fieldName: 'dictType',
      label: '字典类型',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入数据标签',
      },
      fieldName: 'label',
      label: '数据标签',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入数据键值',
      },
      fieldName: 'value',
      label: '数据键值',
      rules: 'required',
    },
    {
      component: 'InputNumber',
      componentProps: {
        placeholder: '请输入显示排序',
      },
      fieldName: 'sort',
      label: '显示排序',
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
      component: 'Select',
      componentProps: {
        options: colorOptions,
        placeholder: '请选择颜色类型',
      },
      fieldName: 'colorType',
      label: '颜色类型',
    },
    {
      component: 'TagEditor',
      fieldName: 'tagStyle',
      help: '标签样式是最高优先级，会覆盖颜色类型',
      label: '标签样式',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '如 ai:knowledge:scope-enterprise，空表示无需权限',
      },
      fieldName: 'permission',
      help: '设置后，前端下拉选项会自动过滤无权用户',
      label: '权限标识',
    },
    {
      component: 'Textarea',
      componentProps: {
        placeholder: '请输入备注',
      },
      fieldName: 'remark',
      label: '备注',
    },
  ];
}

export function useDataGridFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入字典标签',
      },
      fieldName: 'label',
      label: '字典标签',
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

export function useDataGridColumns(
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
      title: '字典编码',
    },
    {
      field: 'label',
      minWidth: 120,
      title: '字典标签',
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
      field: 'colorType',
      minWidth: 120,
      slots: { default: 'colorType' },
      title: '颜色类型',
    },
    {
      cellRender: { name: 'CellTagStyle' },
      field: 'tagStyle',
      minWidth: 120,
      title: '标签样式',
    },
    {
      field: 'value',
      minWidth: 100,
      title: '字典键值',
    },
    {
      field: 'permission',
      minWidth: 180,
      title: '权限标识',
    },
    {
      field: 'sort',
      minWidth: 100,
      title: '字典排序',
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
      minWidth: 120,
      slots: { default: 'actions' },
      title: '操作',
    },
  ];
}
