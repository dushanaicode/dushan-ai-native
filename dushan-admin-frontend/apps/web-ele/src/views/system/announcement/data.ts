import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemAnnouncementApi } from '#/api/system/announcement';

import { z } from '#/adapter/form';
import { DICT_TYPE } from '#/constants/dict-types';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

function requiredString(message: string) {
  return z.string().min(1, message);
}

export function useFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
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
        maxlength: 100,
        placeholder: '请输入公告标题',
        showWordLimit: true,
      },
      fieldName: 'title',
      label: '公告标题',
      rules: 'required',
    },
    {
      component: 'Select',
      componentProps: {
        options: dictionary.getDictOptions(
          DICT_TYPE.SYSTEM_ANNOUNCEMENT_CATEGORY,
          'number',
        ),
        placeholder: '请选择公告类别',
      },
      fieldName: 'category',
      label: '公告类别',
      rules: 'selectRequired',
    },
    {
      component: 'RadioGroup',
      componentProps: {
        isButton: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.SYSTEM_ANNOUNCEMENT_STATUS,
          'number',
        ),
      },
      fieldName: 'status',
      label: '公告状态',
      rules: z.number().default(0),
    },
    {
      component: 'RadioGroup',
      componentProps: {
        isButton: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.INFRA_BOOLEAN_STRING,
          'boolean',
        ),
      },
      fieldName: 'isTop',
      label: '是否置顶',
      rules: z.boolean().default(false),
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: 0,
        placeholder: '请输入排序',
      },
      fieldName: 'sort',
      label: '排序',
      rules: z.number().default(0),
    },
    {
      component: 'Input',
      componentProps: {
        maxlength: 30,
        placeholder: '请输入发布人',
        showWordLimit: true,
      },
      fieldName: 'publisher',
      label: '发布人',
    },
    {
      component: 'DatePicker',
      componentProps: {
        clearable: true,
        placeholder: '请选择发布时间',
        type: 'datetime',
        valueFormat: 'YYYY-MM-DD HH:mm:ss',
      },
      fieldName: 'publishTime',
      label: '发布时间',
    },
    {
      component: 'DatePicker',
      componentProps: {
        clearable: true,
        placeholder: '请选择过期时间',
        type: 'datetime',
        valueFormat: 'YYYY-MM-DD HH:mm:ss',
      },
      fieldName: 'expireTime',
      label: '过期时间',
    },
    {
      component: 'RichTextarea',
      componentProps: {
        imageDirectory: 'announcement',
        minHeight: 280,
        placeholder: '请输入公告内容',
      },
      fieldName: 'content',
      formItemClass: 'col-span-2',
      label: '公告内容',
      rules: requiredString('请输入公告内容'),
    },
  ];
}

export function useGridFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入公告标题',
      },
      fieldName: 'title',
      label: '公告标题',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.SYSTEM_ANNOUNCEMENT_CATEGORY,
          'number',
        ),
        placeholder: '请选择公告类别',
      },
      fieldName: 'category',
      label: '公告类别',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.SYSTEM_ANNOUNCEMENT_STATUS,
          'number',
        ),
        placeholder: '请选择公告状态',
      },
      fieldName: 'status',
      label: '公告状态',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.INFRA_BOOLEAN_STRING,
          'boolean',
        ),
        placeholder: '请选择是否置顶',
      },
      fieldName: 'isTop',
      label: '是否置顶',
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

export function useGridColumns(): VxeTableGridOptions<SystemAnnouncementApi.AnnouncementRespVO>['columns'] {
  return [
    { fixed: 'left', type: 'checkbox', width: 40 },
    {
      field: 'id',
      minWidth: 100,
      title: '公告编号',
    },
    {
      field: 'title',
      minWidth: 220,
      showOverflow: 'tooltip',
      title: '公告标题',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.SYSTEM_ANNOUNCEMENT_CATEGORY },
      },
      field: 'category',
      minWidth: 130,
      title: '公告类别',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.SYSTEM_ANNOUNCEMENT_STATUS },
      },
      field: 'status',
      minWidth: 110,
      title: '公告状态',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.INFRA_BOOLEAN_STRING },
      },
      field: 'isTop',
      minWidth: 100,
      title: '是否置顶',
    },
    {
      field: 'sort',
      minWidth: 80,
      title: '排序',
    },
    {
      field: 'publisher',
      minWidth: 120,
      title: '发布人',
    },
    {
      field: 'publishTime',
      formatter: 'formatDateTime',
      minWidth: 180,
      title: '发布时间',
    },
    {
      field: 'expireTime',
      formatter: 'formatDateTime',
      minWidth: 180,
      title: '过期时间',
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
      minWidth: 230,
      slots: { default: 'actions' },
      title: '操作',
    },
  ];
}
