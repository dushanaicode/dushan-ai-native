import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraApiAccessLogApi } from '#/api/infra/api-access-log';
import type { DescriptionItemSchema } from '#/components';

import { h } from 'vue';

import { JsonViewer } from '@vben/common-ui';
import { formatDateTime } from '@vben/utils';

import { DictTag } from '#/components';
import { DICT_TYPE } from '#/constants/dict-types';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

function formatDuration(duration?: number) {
  return `${duration ?? 0} ms`;
}

function formatResult(row: InfraApiAccessLogApi.ApiAccessLogRespVO) {
  return row.resultCode === 0
    ? '成功'
    : `失败(${row.resultCode}${row.resultMsg ? `, ${row.resultMsg}` : ''})`;
}

/** API 访问日志搜索表单 */
export function useGridFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
    {
      component: 'InputNumber',
      componentProps: {
        clearable: true,
        controls: false,
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
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入应用名',
      },
      fieldName: 'applicationName',
      label: '应用名',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入请求地址',
      },
      fieldName: 'requestUrl',
      label: '请求地址',
    },
    {
      component: 'RangePicker',
      componentProps: {
        ...getRangePickerDefaultProps(),
        clearable: true,
      },
      fieldName: 'beginTime',
      label: '请求时间',
    },
    {
      component: 'InputNumber',
      componentProps: {
        clearable: true,
        controls: false,
        min: 0,
        placeholder: '请输入最小执行时长',
      },
      fieldName: 'duration',
      label: '执行时长',
    },
    {
      component: 'InputNumber',
      componentProps: {
        clearable: true,
        controls: false,
        placeholder: '请输入结果码',
      },
      fieldName: 'resultCode',
      label: '结果码',
    },
  ];
}

/** API 访问日志表格列 */
export function useGridColumns(): VxeTableGridOptions<InfraApiAccessLogApi.ApiAccessLogRespVO>['columns'] {
  return [
    {
      field: 'id',
      minWidth: 100,
      title: '日志编号',
    },
    {
      field: 'traceId',
      minWidth: 220,
      showOverflow: 'tooltip',
      title: '链路追踪',
    },
    {
      field: 'userId',
      minWidth: 100,
      title: '用户编号',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.USER_TYPE },
      },
      field: 'userType',
      minWidth: 110,
      title: '用户类型',
    },
    {
      field: 'applicationName',
      minWidth: 140,
      title: '应用名',
    },
    {
      field: 'requestMethod',
      minWidth: 90,
      title: '请求方法',
    },
    {
      field: 'requestUrl',
      minWidth: 260,
      showOverflow: 'tooltip',
      title: '请求地址',
    },
    {
      field: 'beginTime',
      formatter: 'formatDateTime',
      minWidth: 180,
      title: '请求时间',
    },
    {
      field: 'duration',
      formatter: ({ row }) => formatDuration(row.duration),
      minWidth: 110,
      title: '执行时长',
    },
    {
      field: 'resultCode',
      formatter: ({ row }) => formatResult(row),
      minWidth: 160,
      title: '操作结果',
    },
    {
      field: 'operateModule',
      minWidth: 140,
      title: '操作模块',
    },
    {
      field: 'operateName',
      minWidth: 180,
      showOverflow: 'tooltip',
      title: '操作名',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.INFRA_OPERATE_TYPE },
      },
      field: 'operateType',
      minWidth: 110,
      title: '操作类型',
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

/** API 访问日志详情字段 */
export function useDetailSchema(): DescriptionItemSchema[] {
  return [
    { field: 'id', label: '日志编号' },
    { field: 'traceId', label: '链路追踪', span: 2 },
    { field: 'applicationName', label: '应用名' },
    { field: 'userId', label: '用户编号' },
    {
      content: (data) =>
        h(DictTag, {
          type: DICT_TYPE.USER_TYPE,
          value: data.userType,
        }),
      field: 'userType',
      label: '用户类型',
    },
    { field: 'userIp', label: '用户 IP' },
    { field: 'userAgent', label: '用户 UA', span: 2 },
    {
      content: (data) => `${data.requestMethod} ${data.requestUrl}`,
      field: 'requestMethod',
      label: '请求信息',
      span: 2,
    },
    {
      content: (data) =>
        h(JsonViewer, {
          previewMode: true,
          value: data.requestParams,
        }),
      field: 'requestParams',
      label: '请求参数',
      span: 2,
    },
    {
      content: (data) =>
        h(JsonViewer, {
          previewMode: true,
          value: data.responseBody,
        }),
      field: 'responseBody',
      label: '响应结果',
      span: 2,
    },
    {
      content: (data) =>
        `${formatDateTime(data.beginTime)} ~ ${formatDateTime(data.endTime)}`,
      field: 'beginTime',
      label: '请求时间',
      span: 2,
    },
    {
      content: (data) => formatDuration(data.duration),
      field: 'duration',
      label: '请求耗时',
    },
    {
      content: (data) =>
        formatResult(data as InfraApiAccessLogApi.ApiAccessLogRespVO),
      field: 'resultCode',
      label: '操作结果',
    },
    { field: 'operateModule', label: '操作模块' },
    { field: 'operateName', label: '操作名' },
    {
      content: (data) =>
        h(DictTag, {
          type: DICT_TYPE.INFRA_OPERATE_TYPE,
          value: data.operateType,
        }),
      field: 'operateType',
      label: '操作类型',
    },
  ];
}
