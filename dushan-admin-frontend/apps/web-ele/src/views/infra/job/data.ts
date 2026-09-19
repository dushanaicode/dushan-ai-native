import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraJobApi } from '#/api/infra/job';
import type { DescriptionItemSchema } from '#/components';

import { h, markRaw } from 'vue';

import { formatDateTime } from '@vben/utils';

import { ElTimeline, ElTimelineItem } from 'element-plus';

import { CronTab, DictTag } from '#/components';
import { DICT_TYPE } from '#/constants/dict-types';
import { InfraJobStatusEnum } from '#/constants/enums';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

function formatMilliseconds(value?: null | number) {
  return value && value > 0 ? `${value} ms` : '未开启';
}

function renderNextTimes(data: unknown) {
  const nextTimes = (data as undefined | { nextTimes?: string[] })?.nextTimes;
  if (!nextTimes?.length) {
    return '无后续执行时间';
  }

  return h(ElTimeline, {}, () =>
    nextTimes.map((time) =>
      h(ElTimelineItem, {}, () => formatDateTime(time)?.toString() || time),
    ),
  );
}

/** 新增/编辑定时任务表单 */
export function useFormSchema(): VbenFormSchema[] {
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
        placeholder: '请输入任务名称',
      },
      fieldName: 'name',
      label: '任务名称',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: (ctx) => ({
        disabled: !!ctx.rootValues?.id,
        placeholder: '请输入处理器名称',
      }),
      dependencies: {
        triggerFields: ['id'],
      },
      fieldName: 'handlerName',
      label: '处理器名称',
      rules: 'required',
    },
    {
      component: 'Textarea',
      componentProps: {
        placeholder: '请输入处理器参数',
        rows: 3,
      },
      fieldName: 'handlerParam',
      formItemClass: 'col-span-2',
      label: '处理器参数',
    },
    {
      component: markRaw(CronTab),
      componentProps: {
        placeholder: '请输入 CRON 表达式',
      },
      defaultValue: '* * * * *',
      fieldName: 'cronExpression',
      formItemClass: 'col-span-2',
      label: 'CRON 表达式',
      rules: 'required',
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: 0,
        placeholder: '请输入重试次数，0 表示不重试',
      },
      defaultValue: 0,
      fieldName: 'retryCount',
      label: '重试次数',
      rules: 'required',
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: 0,
        placeholder: '请输入重试间隔，单位毫秒',
      },
      defaultValue: 0,
      fieldName: 'retryInterval',
      label: '重试间隔',
      rules: 'required',
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: 0,
        placeholder: '请输入监控超时时间，单位毫秒',
      },
      fieldName: 'monitorTimeout',
      label: '监控超时',
    },
  ];
}

/** 定时任务搜索表单 */
export function useGridFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入任务名称',
      },
      fieldName: 'name',
      label: '任务名称',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.INFRA_JOB_STATUS,
          'number',
        ),
        placeholder: '请选择任务状态',
      },
      fieldName: 'status',
      label: '任务状态',
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
      fieldName: 'createTime',
      label: '创建时间',
    },
  ];
}

/** 定时任务表格列 */
export function useGridColumns(
  onStatusChange?: (
    newStatus: number,
    row: InfraJobApi.JobRespVO,
  ) => Promise<boolean | undefined>,
): VxeTableGridOptions<InfraJobApi.JobRespVO>['columns'] {
  return [
    { fixed: 'left', type: 'checkbox', width: 40 },
    {
      field: 'id',
      minWidth: 90,
      title: '任务编号',
    },
    {
      field: 'name',
      minWidth: 160,
      showOverflow: 'tooltip',
      title: '任务名称',
    },
    {
      align: 'center',
      cellRender: {
        attrs: { beforeChange: onStatusChange },
        name: 'CellSwitch',
        props: {
          checkedValue: InfraJobStatusEnum.NORMAL,
          unCheckedValue: InfraJobStatusEnum.STOP,
        },
      },
      field: 'status',
      minWidth: 100,
      title: '任务状态',
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
      field: 'cronExpression',
      minWidth: 150,
      title: 'CRON 表达式',
    },
    {
      field: 'retryCount',
      minWidth: 90,
      title: '重试次数',
    },
    {
      field: 'retryInterval',
      minWidth: 120,
      title: '重试间隔(ms)',
    },
    {
      field: 'monitorTimeout',
      formatter: ({ row }) => formatMilliseconds(row.monitorTimeout),
      minWidth: 130,
      title: '监控超时',
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
      width: 170,
    },
  ];
}

/** 定时任务详情字段 */
export function useDetailSchema(): DescriptionItemSchema[] {
  return [
    { field: 'id', label: '任务编号' },
    { field: 'name', label: '任务名称' },
    {
      content: (data) =>
        h(DictTag, {
          type: DICT_TYPE.INFRA_JOB_STATUS,
          value: data?.status,
        }),
      field: 'status',
      label: '任务状态',
    },
    { field: 'handlerName', label: '处理器名称' },
    { field: 'handlerParam', label: '处理器参数', span: 2 },
    { field: 'cronExpression', label: 'CRON 表达式' },
    { field: 'retryCount', label: '重试次数' },
    {
      content: (data) => `${data?.retryInterval ?? 0} ms`,
      field: 'retryInterval',
      label: '重试间隔',
    },
    {
      content: (data) => formatMilliseconds(data?.monitorTimeout),
      field: 'monitorTimeout',
      label: '监控超时',
    },
    {
      content: renderNextTimes,
      field: 'nextTimes',
      label: '后续执行时间',
      span: 2,
    },
    {
      content: (data) => formatDateTime(data?.createTime),
      field: 'createTime',
      label: '创建时间',
    },
  ];
}
