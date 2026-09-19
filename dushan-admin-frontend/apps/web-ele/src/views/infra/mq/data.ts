import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraMqApi } from '#/api/infra/mq';
import type { DescriptionItemSchema } from '#/components';

import { formatDateTime } from '@vben/utils';

import { getRangePickerDefaultProps } from '#/utils/range-picker';

/** MQ 消息定义表单 */
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
        placeholder: '请输入消息主题',
      },
      fieldName: 'topic',
      label: '消息主题',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入消费者名称',
      },
      fieldName: 'consumer',
      label: '消费者名称',
      rules: 'required',
    },
    {
      component: 'InputNumber',
      componentProps: {
        clearable: true,
        min: 0,
        placeholder: '留空则继承全局配置',
      },
      fieldName: 'retryCount',
      label: '重试次数',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入描述',
        rows: 4,
        type: 'textarea',
      },
      fieldName: 'description',
      label: '描述',
    },
  ];
}

/** MQ 消息定义搜索表单 */
export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入消息主题',
      },
      fieldName: 'topic',
      label: '消息主题',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入消费者名称',
      },
      fieldName: 'consumer',
      label: '消费者名称',
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

/** MQ 消息定义表格列 */
export function useGridColumns(): VxeTableGridOptions<InfraMqApi.MqRespVO>['columns'] {
  return [
    {
      fixed: 'left',
      type: 'checkbox',
      width: 60,
    },
    {
      field: 'id',
      minWidth: 80,
      title: '编号',
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
      field: 'retryCount',
      minWidth: 100,
      title: '重试次数',
    },
    {
      field: 'description',
      minWidth: 180,
      showOverflow: 'tooltip',
      title: '描述',
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
      width: 220,
    },
  ];
}

/** MQ 消息定义详情字段 */
export function useDetailSchema(): DescriptionItemSchema[] {
  return [
    { field: 'id', label: '编号' },
    { field: 'topic', label: '消息主题' },
    { field: 'consumer', label: '消费者名称' },
    { field: 'retryCount', label: '重试次数' },
    { field: 'description', label: '描述', span: 2 },
    {
      content: (data) => formatDateTime(data?.createTime),
      field: 'createTime',
      label: '创建时间',
    },
  ];
}
