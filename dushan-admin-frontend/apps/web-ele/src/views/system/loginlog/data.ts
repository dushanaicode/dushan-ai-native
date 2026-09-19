import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { DescriptionItemSchema } from '#/components';

import { h } from 'vue';

import { formatDateTime } from '@vben/utils';

import { DictTag } from '#/components';
import { DICT_TYPE } from '#/constants/dict-types';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

/** 登录日志搜索表单 */
export function useGridFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入用户名',
      },
      fieldName: 'username',
      label: '用户名',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入登录地址',
      },
      fieldName: 'userIp',
      label: '登录地址',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.SYSTEM_LOGIN_TYPE,
          'number',
        ),
        placeholder: '请选择操作类型',
      },
      fieldName: 'logType',
      label: '操作类型',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.SYSTEM_LOGIN_RESULT,
          'number',
        ),
        placeholder: '请选择登录结果',
      },
      fieldName: 'result',
      label: '登录结果',
    },
    {
      component: 'RangePicker',
      componentProps: {
        ...getRangePickerDefaultProps(),
        clearable: true,
      },
      fieldName: 'createTime',
      label: '登录时间',
    },
  ];
}

/** 登录日志列表字段 */
export function useGridColumns(): VxeTableGridOptions['columns'] {
  return [
    {
      field: 'id',
      minWidth: 100,
      title: '日志编号',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.SYSTEM_LOGIN_TYPE },
      },
      field: 'logType',
      minWidth: 120,
      title: '操作类型',
    },
    {
      field: 'username',
      minWidth: 160,
      title: '用户名',
    },
    {
      field: 'userIp',
      minWidth: 160,
      title: '登录地址',
    },
    {
      field: 'userAgent',
      minWidth: 260,
      showOverflow: 'tooltip',
      title: '浏览器',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.SYSTEM_LOGIN_RESULT },
      },
      field: 'result',
      minWidth: 120,
      title: '登录结果',
    },
    {
      field: 'createTime',
      formatter: 'formatDateTime',
      minWidth: 180,
      title: '登录日期',
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

/** 登录日志详情字段 */
export function useDetailSchema(): DescriptionItemSchema[] {
  return [
    {
      field: 'id',
      label: '日志编号',
    },
    {
      field: 'traceId',
      label: '链路追踪',
    },
    {
      field: 'userId',
      label: '用户编号',
    },
    {
      content: (data) =>
        h(DictTag, {
          type: DICT_TYPE.USER_TYPE,
          value: data?.userType,
        }),
      field: 'userType',
      label: '用户类型',
    },
    {
      field: 'username',
      label: '用户名',
    },
    {
      field: 'userIp',
      label: '登录地址',
    },
    {
      contentStyle: {
        wordBreak: 'break-all',
      },
      field: 'userAgent',
      label: '浏览器',
    },
    {
      content: (data) =>
        h(DictTag, {
          type: DICT_TYPE.SYSTEM_LOGIN_TYPE,
          value: data?.logType,
        }),
      field: 'logType',
      label: '操作类型',
    },
    {
      content: (data) =>
        h(DictTag, {
          type: DICT_TYPE.SYSTEM_LOGIN_RESULT,
          value: data?.result,
        }),
      field: 'result',
      label: '登录结果',
    },
    {
      content: (data) => {
        const time = data?.createTime;
        return time ? (formatDateTime(time) as string) : '';
      },
      field: 'createTime',
      label: '登录日期',
    },
  ];
}
