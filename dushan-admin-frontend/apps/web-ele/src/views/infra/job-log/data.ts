import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraJobLogApi } from '#/api/infra/job/log';
import type { DescriptionItemSchema } from '#/components';

import { h } from 'vue';

import { formatDateTime } from '@vben/utils';

import { DictTag } from '#/components';
import { DICT_TYPE } from '#/constants/dict-types';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

function formatDuration(duration?: null | number) {
  return `${duration ?? 0} ms`;
}

function formatExecuteTime(row: InfraJobLogApi.JobLogRespVO) {
  return `${formatDateTime(row.beginTime)} ~ ${row.endTime ? formatDateTime(row.endTime) : '-'}`;
}

/** 定时任务日志搜索表单 */
export function useGridFormSchema(defaultJobId?: number): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
    {
      component: 'InputNumber',
      componentProps: {
        clearable: true,
        controls: false,
        min: 1,
        placeholder: '请输入任务编号',
      },
      defaultValue: defaultJobId,
      fieldName: 'jobId',
      label: '任务编号',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入处理器名称',
      },
      fieldName: 'handlerName',
      label: '处理器名称',
    },
    {
      component: 'RangePicker',
      componentProps: {
        ...getRangePickerDefaultProps(),
        clearable: true,
      },
      fieldName: 'beginEndTime',
      label: '执行时间',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.INFRA_JOB_LOG_STATUS,
          'number',
        ),
        placeholder: '请选择执行状态',
      },
      fieldName: 'status',
      label: '执行状态',
    },
  ];
}

/** 定时任务日志表格列 */
export function useGridColumns(): VxeTableGridOptions<InfraJobLogApi.JobLogRespVO>['columns'] {
  return [
    {
      field: 'id',
      minWidth: 100,
      title: '日志编号',
    },
    {
      field: 'jobId',
      minWidth: 100,
      title: '任务编号',
    },
    {
      field: 'handlerName',
      minWidth: 180,
      showOverflow: 'tooltip',
      title: '处理器名称',
    },
    {
      field: 'handlerParam',
      minWidth: 180,
      showOverflow: 'tooltip',
      title: '处理器参数',
    },
    {
      field: 'executeIndex',
      minWidth: 100,
      title: '执行次数',
    },
    {
      field: 'beginTime',
      formatter: ({ row }) => formatExecuteTime(row),
      minWidth: 280,
      title: '执行时间',
    },
    {
      field: 'duration',
      formatter: ({ row }) => formatDuration(row.duration),
      minWidth: 110,
      title: '执行时长',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.INFRA_JOB_LOG_STATUS },
      },
      field: 'status',
      minWidth: 110,
      title: '执行状态',
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

/** 定时任务日志详情字段 */
export function useDetailSchema(): DescriptionItemSchema[] {
  return [
    { field: 'id', label: '日志编号' },
    { field: 'jobId', label: '任务编号' },
    { field: 'handlerName', label: '处理器名称' },
    { field: 'handlerParam', label: '处理器参数', span: 2 },
    { field: 'executeIndex', label: '执行次数' },
    {
      content: (data) =>
        `${formatDateTime(data?.beginTime)} ~ ${
          data?.endTime ? formatDateTime(data.endTime) : '-'
        }`,
      field: 'beginTime',
      label: '执行时间',
      span: 2,
    },
    {
      content: (data) => formatDuration(data?.duration),
      field: 'duration',
      label: '执行时长',
    },
    {
      content: (data) =>
        h(DictTag, {
          type: DICT_TYPE.INFRA_JOB_LOG_STATUS,
          value: data?.status,
        }),
      field: 'status',
      label: '执行状态',
    },
    {
      content: (data) =>
        h(
          'pre',
          {
            class:
              'max-h-80 overflow-auto whitespace-pre-wrap break-all text-sm leading-6',
          },
          data?.result || '-',
        ),
      field: 'result',
      label: '执行结果',
      span: 2,
    },
    {
      content: (data) => formatDateTime(data?.createTime),
      field: 'createTime',
      label: '创建时间',
    },
  ];
}
