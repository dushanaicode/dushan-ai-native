import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemSmsChannelApi } from '#/api/system/sms/channel';

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
        clearable: true,
        maxlength: 12,
        placeholder: '请输入短信签名',
        showWordLimit: true,
      },
      fieldName: 'signature',
      label: '短信签名',
      rules: 'required',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.SYSTEM_SMS_CHANNEL_CODE,
          'string',
        ),
        placeholder: '请选择渠道编码',
      },
      fieldName: 'code',
      label: '渠道编码',
      rules: 'selectRequired',
    },
    {
      component: 'RadioGroup',
      componentProps: {
        isButton: true,
        options: dictionary.getDictOptions(DICT_TYPE.COMMON_STATUS, 'number'),
      },
      fieldName: 'status',
      label: '启用状态',
      rules: z.number().default(SwitchStatus.ENABLED),
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        maxlength: 128,
        placeholder: '请输入短信 API 的账号',
        showWordLimit: true,
      },
      fieldName: 'apiKey',
      label: 'API 账号',
      rules: 'required',
    },
    {
      component: 'VbenInputPassword',
      componentProps: {
        placeholder: '请输入短信 API 的密钥',
      },
      fieldName: 'apiSecret',
      label: 'API 密钥',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        maxlength: 255,
        placeholder: '请输入短信发送回调 URL',
        showWordLimit: true,
      },
      fieldName: 'callbackUrl',
      formItemClass: 'col-span-2',
      label: '回调 URL',
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
      formItemClass: 'col-span-2',
      label: '备注',
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
        placeholder: '请输入短信签名',
      },
      fieldName: 'signature',
      label: '短信签名',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.SYSTEM_SMS_CHANNEL_CODE,
          'string',
        ),
        placeholder: '请选择渠道编码',
      },
      fieldName: 'code',
      label: '渠道编码',
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
    row: SystemSmsChannelApi.SmsChannelRespVO,
  ) => Promise<boolean | undefined>,
): VxeTableGridOptions<SystemSmsChannelApi.SmsChannelRespVO>['columns'] {
  return [
    { fixed: 'left', type: 'checkbox', width: 40 },
    {
      field: 'id',
      minWidth: 100,
      title: '编号',
    },
    {
      field: 'signature',
      minWidth: 140,
      title: '短信签名',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.SYSTEM_SMS_CHANNEL_CODE },
      },
      field: 'code',
      minWidth: 150,
      title: '渠道编码',
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
      field: 'apiKey',
      minWidth: 180,
      showOverflow: 'tooltip',
      title: 'API 账号',
    },
    {
      field: 'apiSecret',
      minWidth: 180,
      showOverflow: 'tooltip',
      title: 'API 密钥',
    },
    {
      field: 'callbackUrl',
      minWidth: 220,
      showOverflow: 'tooltip',
      title: '回调 URL',
    },
    {
      field: 'remark',
      minWidth: 160,
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
      fixed: 'right',
      minWidth: 130,
      slots: { default: 'actions' },
      title: '操作',
    },
  ];
}
