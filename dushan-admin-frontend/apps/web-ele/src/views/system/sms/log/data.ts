import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemSmsLogApi } from '#/api/system/sms/log';

import { getSimpleSmsChannelList } from '#/api/system/sms/channel';
import { DICT_TYPE } from '#/constants/dict-types';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

/** 短信日志搜索表单 */
export function useGridFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入手机号',
      },
      fieldName: 'mobile',
      label: '手机号',
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
      component: 'InputNumber',
      componentProps: {
        clearable: true,
        min: 1,
        placeholder: '请输入模板编号',
      },
      fieldName: 'templateId',
      label: '模板编号',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.SYSTEM_SMS_SEND_STATUS,
          'number',
        ),
        placeholder: '请选择发送状态',
      },
      fieldName: 'sendStatus',
      label: '发送状态',
    },
    {
      component: 'RangePicker',
      componentProps: {
        ...getRangePickerDefaultProps(),
        clearable: true,
      },
      fieldName: 'sendTime',
      label: '发送时间',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.SYSTEM_SMS_RECEIVE_STATUS,
          'number',
        ),
        placeholder: '请选择接收状态',
      },
      fieldName: 'receiveStatus',
      label: '接收状态',
    },
    {
      component: 'RangePicker',
      componentProps: {
        ...getRangePickerDefaultProps(),
        clearable: true,
      },
      fieldName: 'receiveTime',
      label: '接收时间',
    },
  ];
}

/** 短信日志列表字段 */
export function useGridColumns(): VxeTableGridOptions<SystemSmsLogApi.SmsLogRespVO>['columns'] {
  return [
    {
      field: 'id',
      minWidth: 100,
      title: '编号',
    },
    {
      field: 'mobile',
      minWidth: 140,
      title: '手机号',
    },
    {
      field: 'templateContent',
      minWidth: 260,
      showOverflow: 'tooltip',
      title: '短信内容',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.SYSTEM_SMS_SEND_STATUS },
      },
      field: 'sendStatus',
      minWidth: 120,
      title: '发送状态',
    },
    {
      field: 'sendTime',
      formatter: 'formatDateTime',
      minWidth: 180,
      title: '发送时间',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.SYSTEM_SMS_RECEIVE_STATUS },
      },
      field: 'receiveStatus',
      minWidth: 120,
      title: '接收状态',
    },
    {
      field: 'receiveTime',
      formatter: 'formatDateTime',
      minWidth: 180,
      title: '接收时间',
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
      field: 'templateId',
      minWidth: 120,
      title: '模板编号',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.SYSTEM_SMS_TEMPLATE_TYPE },
      },
      field: 'templateType',
      minWidth: 120,
      title: '短信类型',
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
      slots: { default: 'actions' },
      title: '操作',
      width: 90,
    },
  ];
}
