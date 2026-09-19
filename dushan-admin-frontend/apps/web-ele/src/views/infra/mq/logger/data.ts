import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraMqLogApi } from '#/api/infra/mq/log';
import type { DescriptionItemSchema } from '#/components';

import { h } from 'vue';

import { formatDateTime } from '@vben/utils';

import { DictTag } from '#/components';
import { DICT_TYPE } from '#/constants/dict-types';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

function formatDuration(duration?: null | number) {
  return duration === undefined || duration === null ? '-' : `${duration} ms`;
}

function formatConsumeTime(row: InfraMqLogApi.MqLogRespVO) {
  return `${formatDateTime(row.beginTime)} ~ ${
    row.endTime ? formatDateTime(row.endTime) : '-'
  }`;
}

function formatPayload(payload: unknown) {
  if (payload === undefined || payload === null || payload === '') {
    return '-';
  }

  return typeof payload === 'string'
    ? payload
    : JSON.stringify(payload, null, 2);
}

/** MQ 消费日志搜索表单 */
export function useGridFormSchema(defaultConsumer?: string): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入消费者名称',
      },
      defaultValue: defaultConsumer,
      fieldName: 'consumer',
      label: '消费者名称',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入消息 ID',
      },
      fieldName: 'messageId',
      label: '消息 ID',
    },
    {
      component: 'RangePicker',
      componentProps: {
        ...getRangePickerDefaultProps(),
        clearable: true,
      },
      fieldName: 'beginEndTime',
      label: '消费时间',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.INFRA_MQ_LOG_STATUS,
          'number',
        ),
        placeholder: '请选择消费状态',
      },
      fieldName: 'status',
      label: '消费状态',
    },
  ];
}

/** MQ 消费日志表格列 */
export function useGridColumns(): VxeTableGridOptions<InfraMqLogApi.MqLogRespVO>['columns'] {
  return [
    {
      field: 'id',
      minWidth: 90,
      title: '日志编号',
    },
    {
      field: 'messageId',
      minWidth: 220,
      showOverflow: 'tooltip',
      title: '消息 ID',
    },
    {
      field: 'topic',
      minWidth: 160,
      showOverflow: 'tooltip',
      title: '消息主题',
    },
    {
      field: 'consumer',
      minWidth: 180,
      showOverflow: 'tooltip',
      title: '消费者名称',
    },
    {
      field: 'executeIndex',
      minWidth: 100,
      title: '消费次数',
    },
    {
      field: 'beginTime',
      formatter: ({ row }) => formatConsumeTime(row),
      minWidth: 280,
      title: '消费时间',
    },
    {
      field: 'duration',
      formatter: ({ row }) => formatDuration(row.duration),
      minWidth: 110,
      title: '消费时长',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.INFRA_MQ_LOG_STATUS },
      },
      field: 'status',
      minWidth: 110,
      title: '消费状态',
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

/** MQ 消费日志详情字段 */
export function useDetailSchema(): DescriptionItemSchema[] {
  return [
    { field: 'id', label: '日志编号' },
    { field: 'messageId', label: '消息 ID', span: 2 },
    { field: 'topic', label: '消息主题' },
    { field: 'consumer', label: '消费者名称' },
    { field: 'executeIndex', label: '消费次数' },
    {
      content: (data) =>
        `${formatDateTime(data?.beginTime)} ~ ${
          data?.endTime ? formatDateTime(data.endTime) : '-'
        }`,
      field: 'beginTime',
      label: '消费时间',
      span: 2,
    },
    {
      content: (data) => formatDuration(data?.duration),
      field: 'duration',
      label: '消费时长',
    },
    {
      content: (data) =>
        h(DictTag, {
          type: DICT_TYPE.INFRA_MQ_LOG_STATUS,
          value: data?.status,
        }),
      field: 'status',
      label: '消费状态',
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
      label: '消费结果',
      span: 2,
    },
    {
      content: (data) =>
        h(
          'pre',
          {
            class:
              'max-h-80 overflow-auto whitespace-pre-wrap break-all text-sm leading-6',
          },
          formatPayload(data?.payload),
        ),
      field: 'payload',
      label: '消息负载',
      span: 2,
    },
    {
      content: (data) => formatDateTime(data?.createTime),
      field: 'createTime',
      label: '创建时间',
    },
  ];
}
