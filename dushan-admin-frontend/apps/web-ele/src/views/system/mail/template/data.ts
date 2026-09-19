import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemMailTemplateApi } from '#/api/system/mail/template';

import { z } from '#/adapter/form';
import { getSimpleMailAccountList } from '#/api/system/mail/account';
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
        clearable: true,
        maxlength: 50,
        placeholder: '请输入模板名称',
        showWordLimit: true,
      },
      fieldName: 'name',
      label: '模板名称',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        maxlength: 50,
        placeholder: '请输入模板编码',
        showWordLimit: true,
      },
      fieldName: 'code',
      label: '模板编码',
      rules: 'required',
    },
    {
      component: 'ApiSelect',
      componentProps: {
        api: getSimpleMailAccountList,
        clearable: true,
        labelField: 'mail',
        placeholder: '请选择邮箱账号',
        valueField: 'id',
      },
      fieldName: 'accountId',
      label: '邮箱账号',
      rules: 'selectRequired',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        maxlength: 50,
        placeholder: '请输入发件人名称',
        showWordLimit: true,
      },
      fieldName: 'nickname',
      label: '发件人名称',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        maxlength: 100,
        placeholder: '请输入邮件标题',
        showWordLimit: true,
      },
      fieldName: 'title',
      label: '邮件标题',
      rules: 'required',
    },
    {
      component: 'Textarea',
      componentProps: {
        clearable: true,
        placeholder: '请输入参数名称，多个参数请换行分隔',
        rows: 3,
      },
      fieldName: 'params',
      label: '模板参数',
    },
    {
      component: 'RichTextarea',
      componentProps: {
        minHeight: 260,
        placeholder: '请输入邮件内容',
      },
      fieldName: 'content',
      formItemClass: 'col-span-2',
      label: '邮件内容',
      rules: 'required',
    },
    {
      component: 'RadioGroup',
      componentProps: {
        isButton: true,
        options: dictionary.getDictOptions(DICT_TYPE.COMMON_STATUS, 'number'),
      },
      fieldName: 'status',
      label: '开启状态',
      rules: z.number().default(SwitchStatus.ENABLED),
    },
    {
      component: 'Textarea',
      componentProps: {
        clearable: true,
        maxlength: 255,
        placeholder: '请输入备注',
        rows: 3,
        showWordLimit: true,
      },
      fieldName: 'remark',
      label: '备注',
    },
  ];
}

/** 发送邮件表单 */
export function useSendMailFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Textarea',
      componentProps: {
        disabled: true,
        rows: 4,
      },
      fieldName: 'content',
      formItemClass: 'col-span-2',
      label: '模板内容',
    },
    {
      component: 'Textarea',
      componentProps: {
        placeholder: '请输入收件邮箱，每行一个邮箱地址',
        rows: 3,
      },
      fieldName: 'toMails',
      formItemClass: 'col-span-2',
      label: '收件邮箱',
      rules: 'required',
    },
    {
      component: 'Textarea',
      componentProps: {
        placeholder: '请输入抄送邮箱，每行一个邮箱地址',
        rows: 2,
      },
      fieldName: 'ccMails',
      formItemClass: 'col-span-2',
      label: '抄送邮箱',
    },
    {
      component: 'Textarea',
      componentProps: {
        placeholder: '请输入密送邮箱，每行一个邮箱地址',
        rows: 2,
      },
      fieldName: 'bccMails',
      formItemClass: 'col-span-2',
      label: '密送邮箱',
    },
  ];
}

/** 列表的搜索表单 */
export function useGridFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(DICT_TYPE.COMMON_STATUS, 'number'),
        placeholder: '请选择开启状态',
      },
      fieldName: 'status',
      label: '开启状态',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入模板编码',
      },
      fieldName: 'code',
      label: '模板编码',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入模板名称',
      },
      fieldName: 'name',
      label: '模板名称',
    },
    {
      component: 'ApiSelect',
      componentProps: {
        api: getSimpleMailAccountList,
        clearable: true,
        labelField: 'mail',
        placeholder: '请选择邮箱账号',
        valueField: 'id',
      },
      fieldName: 'accountId',
      label: '邮箱账号',
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
  getAccountMail?: (accountId: string) => string | undefined,
  onStatusChange?: (
    newStatus: number,
    row: SystemMailTemplateApi.MailTemplateRespVO,
  ) => Promise<boolean | undefined>,
): VxeTableGridOptions<SystemMailTemplateApi.MailTemplateRespVO>['columns'] {
  return [
    { fixed: 'left', type: 'checkbox', width: 40 },
    {
      field: 'id',
      minWidth: 100,
      title: '编号',
    },
    {
      field: 'code',
      minWidth: 150,
      title: '模板编码',
    },
    {
      field: 'name',
      minWidth: 160,
      title: '模板名称',
    },
    {
      field: 'title',
      minWidth: 220,
      title: '邮件标题',
    },
    {
      field: 'accountId',
      formatter: ({ cellValue }) => getAccountMail?.(cellValue) ?? '-',
      minWidth: 180,
      title: '邮箱账号',
    },
    {
      field: 'nickname',
      minWidth: 140,
      title: '发件人名称',
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
      minWidth: 210,
      slots: { default: 'actions' },
      title: '操作',
    },
  ];
}
