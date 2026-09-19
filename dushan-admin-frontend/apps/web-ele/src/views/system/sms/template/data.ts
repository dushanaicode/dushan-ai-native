import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemSmsTemplateApi } from '#/api/system/sms/template';

import { z } from '#/adapter/form';
import { getSimpleSmsChannelList } from '#/api/system/sms/channel';
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
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.SYSTEM_SMS_TEMPLATE_TYPE,
          'number',
        ),
        placeholder: '请选择短信类型',
      },
      fieldName: 'type',
      label: '短信类型',
      rules: 'selectRequired',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        maxlength: 63,
        placeholder: '请输入模板编码',
        showWordLimit: true,
      },
      fieldName: 'code',
      label: '模板编码',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        maxlength: 63,
        placeholder: '请输入模板名称',
        showWordLimit: true,
      },
      fieldName: 'name',
      label: '模板名称',
      rules: 'required',
    },
    {
      component: 'ApiSelect',
      componentProps: {
        api: getSimpleSmsChannelList,
        clearable: true,
        labelField: 'signature',
        placeholder: '请选择短信渠道',
        valueField: 'id',
      },
      fieldName: 'channelId',
      label: '短信渠道',
      rules: 'selectRequired',
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
      component: 'Input',
      componentProps: {
        clearable: true,
        maxlength: 63,
        placeholder: '请输入短信 API 的模板编号',
        showWordLimit: true,
      },
      fieldName: 'apiTemplateId',
      formItemClass: 'col-span-2',
      label: 'API 模板编号',
      rules: 'required',
    },
    {
      component: 'Textarea',
      componentProps: {
        clearable: true,
        maxlength: 255,
        placeholder: '请输入模板内容',
        rows: 4,
        showWordLimit: true,
      },
      fieldName: 'content',
      formItemClass: 'col-span-2',
      label: '模板内容',
      rules: 'required',
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

/** 发送短信表单 */
export function useSendSmsFormSchema(): VbenFormSchema[] {
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
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入手机号码',
      },
      fieldName: 'mobile',
      formItemClass: 'col-span-2',
      label: '手机号码',
      rules: 'required',
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
        options: dictionary.getDictOptions(
          DICT_TYPE.SYSTEM_SMS_TEMPLATE_TYPE,
          'number',
        ),
        placeholder: '请选择短信类型',
      },
      fieldName: 'type',
      label: '短信类型',
    },
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
        placeholder: '请输入模板内容',
      },
      fieldName: 'content',
      label: '模板内容',
    },
    {
      component: 'ApiSelect',
      componentProps: {
        api: getSimpleSmsChannelList,
        clearable: true,
        labelField: 'signature',
        placeholder: '请选择短信渠道',
        valueField: 'id',
      },
      fieldName: 'channelId',
      label: '短信渠道',
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
    row: SystemSmsTemplateApi.SmsTemplateRespVO,
  ) => Promise<boolean | undefined>,
): VxeTableGridOptions<SystemSmsTemplateApi.SmsTemplateRespVO>['columns'] {
  return [
    { fixed: 'left', type: 'checkbox', width: 40 },
    {
      field: 'id',
      minWidth: 100,
      title: '编号',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.SYSTEM_SMS_TEMPLATE_TYPE },
      },
      field: 'type',
      minWidth: 120,
      title: '短信类型',
    },
    {
      field: 'code',
      minWidth: 150,
      showOverflow: 'tooltip',
      title: '模板编码',
    },
    {
      field: 'name',
      minWidth: 150,
      showOverflow: 'tooltip',
      title: '模板名称',
    },
    {
      field: 'content',
      minWidth: 260,
      showOverflow: 'tooltip',
      title: '模板内容',
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
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.COMMON_BUILTIN_TYPE },
      },
      field: 'builtin',
      minWidth: 110,
      title: '内置类型',
    },
    {
      field: 'apiTemplateId',
      minWidth: 180,
      showOverflow: 'tooltip',
      title: 'API 模板编号',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.SYSTEM_SMS_CHANNEL_CODE },
      },
      field: 'channelCode',
      minWidth: 120,
      title: '短信渠道',
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
