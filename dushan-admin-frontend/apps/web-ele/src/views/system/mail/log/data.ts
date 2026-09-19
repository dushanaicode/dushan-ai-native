import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';

import { getSimpleMailAccountList } from '#/api/system/mail/account';
import { DICT_TYPE } from '#/constants/dict-types';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

/** 邮件日志搜索表单 */
export function useGridFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
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
          DICT_TYPE.SYSTEM_MAIL_SEND_STATUS,
          'number',
        ),
        placeholder: '请选择发送状态',
      },
      fieldName: 'sendStatus',
      label: '发送状态',
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
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入模板编码',
      },
      fieldName: 'templateCode',
      label: '模板编码',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入模板标题',
      },
      fieldName: 'templateTitle',
      label: '模板标题',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入发件邮箱',
      },
      fieldName: 'fromMail',
      label: '发件邮箱',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入收件邮箱',
      },
      fieldName: 'toMail',
      label: '收件邮箱',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入账号用户名',
      },
      fieldName: 'accountUsername',
      label: '账号用户名',
    },
    {
      component: 'InputNumber',
      componentProps: {
        clearable: true,
        min: 1,
        placeholder: '请输入用户编号',
      },
      fieldName: 'userId',
      label: '用户编号',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(DICT_TYPE.USER_TYPE, 'number'),
        placeholder: '请选择用户类型',
      },
      fieldName: 'userType',
      label: '用户类型',
    },
  ];
}

/** 邮件日志列表字段 */
export function useGridColumns(): VxeTableGridOptions['columns'] {
  return [
    {
      field: 'id',
      minWidth: 100,
      title: '日志编号',
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
        props: { type: DICT_TYPE.SYSTEM_MAIL_SEND_STATUS },
      },
      field: 'sendStatus',
      minWidth: 120,
      title: '发送状态',
    },
    {
      field: 'toMail',
      minWidth: 200,
      showOverflow: 'tooltip',
      title: '收件邮箱',
    },
    {
      field: 'fromMail',
      minWidth: 200,
      showOverflow: 'tooltip',
      title: '发件邮箱',
    },
    {
      field: 'templateTitle',
      minWidth: 220,
      showOverflow: 'tooltip',
      title: '模板标题',
    },
    {
      field: 'templateCode',
      minWidth: 160,
      showOverflow: 'tooltip',
      title: '模板编码',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.USER_TYPE },
      },
      field: 'userType',
      minWidth: 120,
      title: '用户类型',
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
      width: 90,
    },
  ];
}
