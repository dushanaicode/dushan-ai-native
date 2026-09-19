import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemNoticeMessageApi } from '#/api/system/notification/notice-message';

import { DICT_TYPE } from '#/constants/dict-types';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

function stripHtml(value?: string) {
  return (value || '')
    .replaceAll(/<[^>]*>/g, '')
    .replaceAll('&nbsp;', ' ')
    .trim();
}

export function useGridFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
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
          DICT_TYPE.INFRA_BOOLEAN_STRING,
          'boolean',
        ),
        placeholder: '请选择已读状态',
      },
      fieldName: 'readStatus',
      label: '已读状态',
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

export function useGridColumns(): VxeTableGridOptions<SystemNoticeMessageApi.NoticeMessageRespVO>['columns'] {
  return [
    { fixed: 'left', type: 'checkbox', width: 40 },
    {
      field: 'id',
      minWidth: 100,
      title: '消息编号',
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
      field: 'noticeContent',
      formatter: ({ cellValue }) => stripHtml(cellValue),
      minWidth: 260,
      showOverflow: 'tooltip',
      title: '通知内容',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.INFRA_BOOLEAN_STRING },
      },
      field: 'readStatus',
      minWidth: 100,
      title: '已读状态',
    },
    {
      field: 'readTime',
      formatter: 'formatDateTime',
      minWidth: 180,
      title: '阅读时间',
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
      minWidth: 120,
      slots: { default: 'actions' },
      title: '操作',
    },
  ];
}
