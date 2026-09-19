import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemTenantApi } from '#/api/system/tenant';

import { z } from '#/adapter/form';
import { getSimpleTenantPackageList } from '#/api/system/tenant/package';
import { DICT_TYPE } from '#/constants/dict-types';
import { SwitchStatus } from '#/constants/status';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

function requiredString(message: string) {
  return z.string().min(1, message);
}

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
        placeholder: '请输入租户名称',
        showWordLimit: true,
      },
      fieldName: 'name',
      label: '租户名称',
      rules: 'required',
    },
    {
      component: 'ApiSelect',
      componentProps: {
        api: getSimpleTenantPackageList,
        clearable: true,
        labelField: 'name',
        placeholder: '请选择租户套餐',
        valueField: 'id',
      },
      fieldName: 'packageId',
      label: '租户套餐',
      rules: 'selectRequired',
    },
    {
      component: 'Input',
      componentProps: {
        maxlength: 30,
        placeholder: '请输入联系人',
        showWordLimit: true,
      },
      fieldName: 'contactName',
      label: '联系人',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入联系手机',
      },
      fieldName: 'contactMobile',
      label: '联系手机',
      rules: 'mobile',
    },
    {
      component: 'Input',
      componentProps: {
        maxlength: 30,
        placeholder: '请输入用户账号',
        showWordLimit: true,
      },
      dependencies: {
        rules: (values) =>
          values.id
            ? z.string().optional()
            : requiredString('请输入用户账号')
                .min(4, '用户账号长度为 4-30 个字符')
                .max(30, '用户账号长度为 4-30 个字符')
                .regex(/^[a-zA-Z0-9]+$/, '用户账号由数字、字母组成'),
        show: (values) => !values.id,
        triggerFields: ['id'],
      },
      fieldName: 'username',
      label: '用户账号',
    },
    {
      component: 'VbenInputPassword',
      componentProps: {
        passwordStrength: true,
        placeholder: '请输入用户密码',
      },
      dependencies: {
        rules: (values) =>
          values.id
            ? z.string().optional()
            : requiredString('请输入用户密码')
                .min(4, '密码长度为 4-16 位')
                .max(16, '密码长度为 4-16 位'),
        show: (values) => !values.id,
        triggerFields: ['id'],
      },
      fieldName: 'password',
      label: '用户密码',
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: 0,
        placeholder: '请输入账号额度',
      },
      fieldName: 'accountCount',
      label: '账号额度',
      rules: 'required',
    },
    {
      component: 'DatePicker',
      componentProps: {
        format: 'YYYY-MM-DD HH:mm:ss',
        placeholder: '请选择过期时间',
        type: 'datetime',
        valueFormat: 'YYYY-MM-DD HH:mm:ss',
      },
      fieldName: 'expireTime',
      label: '过期时间',
      rules: 'required',
    },
    {
      component: 'Textarea',
      componentProps: {
        clearable: true,
        placeholder: '请输入绑定域名，多个域名请换行分隔',
        rows: 3,
      },
      fieldName: 'websites',
      label: '绑定域名',
    },
    {
      component: 'RadioGroup',
      componentProps: {
        isButton: true,
        options: dictionary.getDictOptions(DICT_TYPE.COMMON_STATUS, 'number'),
      },
      fieldName: 'status',
      label: '租户状态',
      rules: z.number().default(SwitchStatus.ENABLED),
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
        placeholder: '请输入租户名称',
      },
      fieldName: 'name',
      label: '租户名称',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入联系人',
      },
      fieldName: 'contactName',
      label: '联系人',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入联系手机',
      },
      fieldName: 'contactMobile',
      label: '联系手机',
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
  getPackageName?: (packageId: string) => string | undefined,
  onStatusChange?: (
    newStatus: number,
    row: SystemTenantApi.TenantRespVO,
  ) => Promise<boolean | undefined>,
): VxeTableGridOptions<SystemTenantApi.TenantRespVO>['columns'] {
  return [
    { fixed: 'left', type: 'checkbox', width: 40 },
    {
      field: 'id',
      minWidth: 100,
      title: '租户编号',
    },
    {
      field: 'name',
      minWidth: 160,
      title: '租户名称',
    },
    {
      field: 'packageId',
      formatter: ({ cellValue }) => getPackageName?.(cellValue) ?? '-',
      minWidth: 160,
      title: '租户套餐',
    },
    {
      field: 'contactName',
      minWidth: 120,
      title: '联系人',
    },
    {
      field: 'contactMobile',
      minWidth: 130,
      title: '联系手机',
    },
    {
      field: 'accountCount',
      minWidth: 100,
      title: '账号额度',
    },
    {
      field: 'expireTime',
      formatter: 'formatDateTime',
      minWidth: 180,
      title: '过期时间',
    },
    {
      field: 'websites',
      formatter: ({ cellValue }) =>
        Array.isArray(cellValue) && cellValue.length > 0
          ? cellValue.join(', ')
          : '-',
      minWidth: 220,
      title: '绑定域名',
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
