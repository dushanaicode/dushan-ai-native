import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraDataSourceConfigApi } from '#/api/infra/data-source-config';

import { markRaw } from 'vue';

import { z } from '#/adapter/form';
import { DataSourceUrl } from '#/components/data-source-url';
import { DICT_TYPE } from '#/constants/dict-types';
import { InfraDbTypeEnum } from '#/constants/enums';
import { SwitchStatus } from '#/constants/status';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

const dbTypeOptions = Object.values(InfraDbTypeEnum).map((item) => ({
  label: item.label,
  value: item.value,
}));

const dbTypeLabelMap = Object.fromEntries(
  dbTypeOptions.map((item) => [item.value, item.label]),
);

/** 新增/编辑表单 */
export function useFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  const booleanOptions = dictionary.getDictOptions(
    DICT_TYPE.INFRA_BOOLEAN_STRING,
    'boolean',
  );
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
        placeholder: '请输入数据源名称',
      },
      fieldName: 'name',
      label: '数据源名称',
      rules: 'required',
    },
    {
      component: markRaw(DataSourceUrl),
      componentProps: {
        placeholder: '请配置数据源连接',
      },
      fieldName: 'url',
      formItemClass: 'col-span-2',
      label: '连接 URL',
      rules: 'required',
    },
    {
      component: 'RadioGroup',
      componentProps: {
        isButton: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.INFRA_DATA_SOURCE_TYPE,
          'number',
        ),
      },
      defaultValue: 1,
      fieldName: 'sourceType',
      label: '主从类型',
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
      component: 'RadioGroup',
      componentProps: {
        isButton: true,
        options: booleanOptions,
      },
      defaultValue: false,
      fieldName: 'isDefault',
      label: '默认数据源',
    },
    {
      component: 'RadioGroup',
      componentProps: {
        isButton: true,
        options: booleanOptions,
      },
      defaultValue: false,
      fieldName: 'echo',
      label: 'SQL 日志',
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: 1,
        placeholder: '请输入连接池大小',
      },
      defaultValue: 10,
      fieldName: 'poolSize',
      label: '连接池大小',
      rules: 'required',
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: -1,
        placeholder: '请输入最大溢出连接数',
      },
      defaultValue: 20,
      fieldName: 'maxOverflow',
      label: '最大溢出',
      rules: 'required',
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: -1,
        placeholder: '请输入连接最大复用时间',
      },
      defaultValue: 3600,
      fieldName: 'poolRecycle',
      label: '复用时间(秒)',
      rules: 'required',
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: 0,
        placeholder: '请输入获取连接最大等待时间',
      },
      defaultValue: 30,
      fieldName: 'poolTimeout',
      label: '等待时间(秒)',
      rules: 'required',
    },
    {
      component: 'Textarea',
      componentProps: {
        placeholder: '请输入备注',
        rows: 3,
      },
      fieldName: 'remark',
      formItemClass: 'col-span-2',
      label: '备注',
    },
  ];
}

/** 搜索表单 */
export function useGridFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入数据源名称',
      },
      fieldName: 'name',
      label: '数据源名称',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dbTypeOptions,
        placeholder: '请选择数据库类型',
      },
      fieldName: 'dbType',
      label: '数据库类型',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.INFRA_DATA_SOURCE_TYPE,
          'number',
        ),
        placeholder: '请选择主从类型',
      },
      fieldName: 'sourceType',
      label: '主从类型',
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

/** 列表字段 */
export function useGridColumns(
  onStatusChange?: (
    newStatus: number,
    row: InfraDataSourceConfigApi.DataSourceConfigRespVO,
  ) => Promise<boolean | undefined>,
): VxeTableGridOptions<InfraDataSourceConfigApi.DataSourceConfigRespVO>['columns'] {
  return [
    {
      field: 'id',
      minWidth: 90,
      title: '编号',
    },
    {
      field: 'name',
      minWidth: 150,
      showOverflow: 'tooltip',
      title: '数据源名称',
    },
    {
      field: 'dbType',
      formatter: ({ cellValue }) => dbTypeLabelMap[cellValue] || cellValue,
      minWidth: 150,
      title: '数据库类型',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.INFRA_DATA_SOURCE_TYPE },
      },
      field: 'sourceType',
      minWidth: 100,
      title: '主从类型',
    },
    {
      cellRender: {
        attrs: { beforeChange: onStatusChange },
        name: 'CellSwitch',
        props: {
          checkedValue: SwitchStatus.ENABLED,
          unCheckedValue: SwitchStatus.DISABLED,
        },
      },
      field: 'status',
      minWidth: 100,
      title: '状态',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.INFRA_BOOLEAN_STRING },
      },
      field: 'isDefault',
      minWidth: 100,
      title: '默认',
    },
    {
      field: 'poolSize',
      minWidth: 110,
      title: '连接池',
    },
    {
      field: 'maxOverflow',
      minWidth: 110,
      title: '最大溢出',
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
      width: 200,
    },
  ];
}
