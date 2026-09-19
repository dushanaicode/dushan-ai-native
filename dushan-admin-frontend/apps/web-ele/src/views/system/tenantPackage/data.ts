import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemTenantPackageApi } from '#/api/system/tenant/package';

import { z } from '#/adapter/form';
import { DICT_TYPE } from '#/constants/dict-types';
import { SwitchStatus } from '#/constants/status';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

/** 新增/修改的表单 */
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
        placeholder: '请输入套餐名称',
        showWordLimit: true,
      },
      fieldName: 'name',
      label: '套餐名称',
      rules: 'required',
    },
    {
      component: 'Input',
      fieldName: 'menuIds',
      formItemClass: 'col-span-2 items-start',
      label: '菜单权限',
      rules: z.array(z.number()).min(1, '请选择菜单权限'),
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
        maxlength: 255,
        placeholder: '请输入备注',
        rows: 3,
        showWordLimit: true,
      },
      fieldName: 'remark',
      formItemClass: 'col-span-2',
      label: '备注',
    },
    {
      component: 'Divider',
      fieldName: 'dividerAiQuota',
      formItemClass: 'col-span-2',
      renderComponentContent: () => ({
        default: () => 'AI 配额配置',
      }),
    },
    {
      component: 'Switch',
      fieldName: 'aiEnabled',
      label: '启用 AI',
      rules: z.boolean().default(false),
    },
    {
      component: 'Select',
      componentProps: {
        options: [
          { label: '纯配额', value: 1 },
          { label: '纯余额', value: 2 },
          { label: '混合', value: 3 },
        ],
        placeholder: '请选择计费模式',
      },
      dependencies: {
        show: (values) => !!values.aiEnabled,
        triggerFields: ['aiEnabled'],
      },
      fieldName: 'aiBillingMode',
      label: '计费模式',
      rules: z.number().default(1),
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: -1,
        placeholder: '请输入月 Token 额度',
      },
      dependencies: {
        show: (values) => !!values.aiEnabled,
        triggerFields: ['aiEnabled'],
      },
      fieldName: 'aiMonthlyTokenLimit',
      label: '月 Token 额度',
      rules: z.number().default(-1),
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: -1,
        placeholder: '请输入月金额额度',
        precision: 2,
        step: 10,
      },
      dependencies: {
        show: (values) => !!values.aiEnabled,
        triggerFields: ['aiEnabled'],
      },
      fieldName: 'aiMonthlyAmountLimit',
      label: '月金额额度',
      rules: z.number().default(-1),
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: -1,
        placeholder: '请输入日 Token 限额',
      },
      dependencies: {
        show: (values) => !!values.aiEnabled,
        triggerFields: ['aiEnabled'],
      },
      fieldName: 'aiDailyTokenLimit',
      label: '日 Token 限额',
      rules: z.number().default(-1),
    },
  ];
}

/** 列表的搜索表单 */
export function useGridFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入套餐名称',
      },
      fieldName: 'name',
      label: '套餐名称',
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

/** 列表的字段 */
export function useGridColumns(
  onStatusChange?: (
    newStatus: number,
    row: SystemTenantPackageApi.TenantPackageRespVO,
  ) => Promise<boolean | undefined>,
): VxeTableGridOptions<SystemTenantPackageApi.TenantPackageRespVO>['columns'] {
  return [
    { fixed: 'left', type: 'checkbox', width: 40 },
    {
      field: 'id',
      minWidth: 100,
      title: '套餐编号',
    },
    {
      field: 'name',
      minWidth: 160,
      title: '套餐名称',
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
      field: 'menuIds',
      formatter: ({ cellValue }) =>
        Array.isArray(cellValue) ? `${cellValue.length} 个菜单` : '-',
      minWidth: 120,
      title: '菜单权限',
    },
    {
      field: 'quotaConfig',
      formatter: ({ row }) =>
        row.quotaConfig?.ai?.enabled ? 'AI 已启用' : '-',
      minWidth: 120,
      title: '配额配置',
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
      fixed: 'right',
      minWidth: 130,
      slots: { default: 'actions' },
      title: '操作',
    },
  ];
}
