import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraApiErrorLogApi } from '#/api/infra/api-error-log';
import type { DescriptionItemSchema } from '#/components';

import { h } from 'vue';

import { JsonViewer } from '@vben/common-ui';
import { formatDateTime } from '@vben/utils';

import { DictTag } from '#/components';
import { DICT_TYPE } from '#/constants/dict-types';
import { InfraApiErrorLogProcessStatusEnum } from '#/constants/enums';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

function formatNullableTime(value?: null | string) {
  return value ? formatDateTime(value) : '-';
}

/** API 错误日志搜索表单 */
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
      fieldName: 'exceptionTime',
      label: '异常时间',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.INFRA_API_ERROR_LOG_PROCESS_STATUS,
          'number',
        ),
        placeholder: '请选择处理状态',
      },
      defaultValue: InfraApiErrorLogProcessStatusEnum.INIT,
      fieldName: 'processStatus',
      label: '处理状态',
    },
  ];
}

/** API 错误日志表格列 */
export function useGridColumns(): VxeTableGridOptions<InfraApiErrorLogApi.ApiErrorLogRespVO>['columns'] {
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
      minWidth: 240,
      showOverflow: 'tooltip',
      title: '请求地址',
    },
    {
      field: 'exceptionTime',
      formatter: 'formatDateTime',
      minWidth: 180,
      title: '异常时间',
    },
    {
      field: 'exceptionName',
      minWidth: 180,
      showOverflow: 'tooltip',
      title: '异常名',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.INFRA_API_ERROR_LOG_PROCESS_STATUS },
      },
      field: 'processStatus',
      minWidth: 110,
      title: '处理状态',
    },
    {
      align: 'center',
      field: 'operation',
      fixed: 'right',
      slots: { default: 'actions' },
      title: '操作',
      width: 190,
    },
  ];
}

/** API 错误日志详情字段 */
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
      content: (data) => formatDateTime(data.exceptionTime),
      field: 'exceptionTime',
      label: '异常时间',
    },
    { field: 'exceptionName', label: '异常名' },
    { field: 'exceptionMessage', label: '异常消息', span: 2 },
    {
      field: 'exceptionRootCauseMessage',
      label: '根因消息',
      span: 2,
    },
    { field: 'exceptionClassName', label: '异常类名', span: 2 },
    { field: 'exceptionFileName', label: '异常文件' },
    { field: 'exceptionMethodName', label: '异常方法' },
    { field: 'exceptionLineNumber', label: '异常行号' },
    {
      content: (data) =>
        h(
          'pre',
          {
            class:
              'max-h-[420px] overflow-auto whitespace-pre-wrap rounded border p-3 text-xs leading-5',
          },
          data.exceptionStackTrace || '-',
        ),
      field: 'exceptionStackTrace',
      label: '异常堆栈',
      span: 2,
    },
    {
      content: (data) =>
        h(DictTag, {
          type: DICT_TYPE.INFRA_API_ERROR_LOG_PROCESS_STATUS,
          value: data.processStatus,
        }),
      field: 'processStatus',
      label: '处理状态',
    },
    { field: 'processUserId', label: '处理人' },
    {
      content: (data) => formatNullableTime(data.processTime),
      field: 'processTime',
      label: '处理时间',
    },
  ];
}
