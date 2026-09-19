import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemNoticeLogApi } from '#/api/system/notification/notice-log';

import { DICT_TYPE } from '#/constants/dict-types';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

export function useGridFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
    {
      component: 'InputNumber',
      componentProps: {
        clearable: true,
        controls: false,
        placeholder: '请输入通知编号',
      },
      fieldName: 'noticeId',
      label: '通知编号',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入通知标题',
      },
      fieldName: 'noticeTitle',
      label: '通知标题',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.SYSTEM_NOTICE_TYPE,
          'number',
        ),
        placeholder: '请选择通知类型',
      },
      fieldName: 'noticeType',
      label: '通知类型',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.SYSTEM_PUSH_TARGET_TYPE,
          'number',
        ),
        placeholder: '请选择推送目标',
      },
      fieldName: 'pushTargetType',
      label: '推送目标',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.SYSTEM_NOTICE_PUSH_STATUS,
          'number',
        ),
        placeholder: '请选择推送状态',
      },
      fieldName: 'pushStatus',
      label: '推送状态',
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

export function useGridColumns(): VxeTableGridOptions<SystemNoticeLogApi.NoticeLogRespVO>['columns'] {
  return [
    {
      field: 'id',
      minWidth: 100,
      title: '日志编号',
    },
    {
      field: 'noticeId',
      minWidth: 100,
      title: '通知编号',
    },
    {
      field: 'noticeTitle',
      minWidth: 220,
      showOverflow: 'tooltip',
      title: '通知标题',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.SYSTEM_NOTICE_TYPE },
      },
      field: 'noticeType',
      minWidth: 100,
      title: '通知类型',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.SYSTEM_PUSH_TARGET_TYPE },
      },
      field: 'pushTargetType',
      minWidth: 110,
      title: '推送目标',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: {
          multiple: true,
          noWrap: true,
          type: DICT_TYPE.SYSTEM_NOTIFICATION_CHANNEL,
        },
      },
      field: 'pushChannels',
      minWidth: 170,
      title: '推送渠道',
    },
    {
      field: 'totalCount',
      minWidth: 90,
      title: '总数',
    },
    {
      field: 'successCount',
      minWidth: 90,
      title: '成功数',
    },
    {
      field: 'failCount',
      minWidth: 90,
      title: '失败数',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.SYSTEM_NOTICE_PUSH_STATUS },
      },
      field: 'pushStatus',
      minWidth: 110,
      title: '推送状态',
    },
    {
      field: 'publisherInfo',
      formatter: ({ cellValue }) =>
        cellValue?.nickname || cellValue?.username || '-',
      minWidth: 140,
      title: '发布人',
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
      width: 100,
    },
  ];
}
