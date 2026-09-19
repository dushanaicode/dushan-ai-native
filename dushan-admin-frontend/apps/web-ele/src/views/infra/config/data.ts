import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraConfigDataApi } from '#/api/infra/config/data';
import type { InfraConfigTypeApi } from '#/api/infra/config/type';

import { z } from '#/adapter/form';
import { getSimpleConfigTypeList } from '#/api/infra/config/type';
import { DICT_TYPE } from '#/constants/dict-types';
import { SwitchStatus } from '#/constants/status';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

const inputTypeOptions = [
  { label: '文本输入', value: 'input' },
  { label: '数字输入', value: 'number' },
  { label: '多行文本', value: 'textarea' },
  { label: '开关', value: 'switch' },
  { label: '滑块', value: 'slider' },
  { label: '下拉选择', value: 'select' },
];

/** 配置类型新增/编辑表单 */
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
      component: 'Select',
      componentProps: {
        options: dictionary.getDictOptions(
          DICT_TYPE.INFRA_CONFIG_MODULE,
          'string',
        ),
        placeholder: '请选择所属模块',
      },
      fieldName: 'module',
      label: '所属模块',
      rules: z.string().default('system'),
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入配置类型名称',
      },
      fieldName: 'name',
      label: '类型名称',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: (ctx) => ({
        disabled: !!ctx.rootValues?.id,
        placeholder: '请输入配置类型编码',
      }),
      dependencies: {
        triggerFields: [''],
      },
      fieldName: 'code',
      label: '类型编码',
      rules: 'required',
    },
    {
      component: 'RadioGroup',
      componentProps: {
        isButton: true,
        options: dictionary.getDictOptions(DICT_TYPE.COMMON_STATUS, 'number'),
      },
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

/** 配置类型搜索表单 */
export function useTypeGridFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.INFRA_CONFIG_MODULE,
          'string',
        ),
        placeholder: '请选择模块',
      },
      fieldName: 'module',
      label: '所属模块',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入配置类型名称',
      },
      fieldName: 'name',
      label: '类型名称',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入配置类型编码',
      },
      fieldName: 'code',
      label: '类型编码',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(DICT_TYPE.COMMON_STATUS, 'number'),
        placeholder: '请选择状态',
      },
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

/** 配置类型表格列 */
export function useTypeGridColumns(
  onStatusChange?: (
    newStatus: number,
    row: InfraConfigTypeApi.ConfigTypeRespVO,
  ) => Promise<boolean | undefined>,
): VxeTableGridOptions<InfraConfigTypeApi.ConfigTypeRespVO>['columns'] {
  return [
    { fixed: 'left', type: 'checkbox', width: 40 },
    {
      field: 'id',
      minWidth: 100,
      title: '类型编号',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.INFRA_CONFIG_MODULE },
      },
      field: 'module',
      minWidth: 110,
      title: '所属模块',
    },
    {
      field: 'name',
      minWidth: 180,
      title: '类型名称',
    },
    {
      field: 'code',
      minWidth: 200,
      title: '类型编码',
    },
    {
      align: 'center',
      cellRender: {
        attrs: { beforeChange: onStatusChange },
        name: 'CellSwitch',
        props: {
          checkedValue: SwitchStatus.ENABLED,
          unCheckedValue: SwitchStatus.DISABLED,
        },
      },
      field: 'status',
      title: '状态',
      width: 90,
    },
    {
      field: 'remark',
      minWidth: 180,
      showOverflow: 'tooltip',
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
      slots: { default: 'actions' },
      title: '操作',
      width: 130,
    },
  ];
}

/** 配置数据新增/编辑表单 */
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
      component: 'Input',
      dependencies: {
        show: () => false,
        triggerFields: [''],
      },
      fieldName: 'lockTypeId',
    },
    {
      component: 'ApiSelect',
      componentProps: (ctx) => ({
        api: getSimpleConfigTypeList,
        disabled: !!ctx.rootValues?.id || !!ctx.rootValues?.lockTypeId,
        labelField: 'name',
        placeholder: '请选择配置类型',
        valueField: 'id',
      }),
      dependencies: {
        triggerFields: [''],
      },
      fieldName: 'typeId',
      label: '配置类型',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入配置名称',
      },
      fieldName: 'name',
      label: '配置名称',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入配置键名',
      },
      fieldName: 'key',
      label: '配置键名',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入配置键值',
      },
      fieldName: 'value',
      label: '配置键值',
      rules: 'required',
    },
    {
      component: 'Textarea',
      componentProps: {
        placeholder: '请输入配置描述',
      },
      fieldName: 'description',
      label: '配置描述',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: inputTypeOptions,
        placeholder: '请选择控件类型',
      },
      fieldName: 'inputType',
      label: '控件类型',
    },
    {
      component: 'Textarea',
      componentProps: {
        placeholder: '请输入合法 JSON 格式控件属性，如 {"min":0,"max":100}',
      },
      fieldName: 'inputProps',
      label: '控件属性',
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: 0,
        placeholder: '请输入显示顺序',
      },
      defaultValue: 0,
      fieldName: 'sort',
      label: '显示顺序',
    },
    {
      component: 'RadioGroup',
      componentProps: {
        isButton: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.INFRA_BOOLEAN_STRING,
          'boolean',
        ),
      },
      defaultValue: true,
      fieldName: 'visible',
      label: '是否可见',
      rules: 'required',
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

/** 配置数据搜索表单 */
export function useDataGridFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.INFRA_CONFIG_MODULE,
          'string',
        ),
        placeholder: '请选择模块',
      },
      fieldName: 'module',
      label: '所属模块',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入配置名称',
      },
      fieldName: 'name',
      label: '配置名称',
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

/** 配置数据表格列 */
export function useDataGridColumns(): VxeTableGridOptions<InfraConfigDataApi.ConfigDataRespVO>['columns'] {
  return [
    { fixed: 'left', type: 'checkbox', width: 40 },
    {
      field: 'id',
      minWidth: 100,
      title: '配置编号',
    },
    {
      field: 'typeName',
      minWidth: 160,
      title: '配置类型',
    },
    {
      field: 'name',
      minWidth: 160,
      title: '配置名称',
    },
    {
      field: 'key',
      minWidth: 180,
      title: '配置键名',
    },
    {
      field: 'value',
      minWidth: 180,
      showOverflow: 'tooltip',
      title: '配置键值',
    },
    {
      field: 'description',
      minWidth: 200,
      showOverflow: 'tooltip',
      title: '配置描述',
    },
    {
      field: 'inputType',
      minWidth: 110,
      title: '控件类型',
    },
    {
      field: 'sort',
      minWidth: 80,
      title: '排序',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.INFRA_BOOLEAN_STRING },
      },
      field: 'visible',
      minWidth: 100,
      title: '是否可见',
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
      slots: { default: 'actions' },
      title: '操作',
      width: 130,
    },
  ];
}
