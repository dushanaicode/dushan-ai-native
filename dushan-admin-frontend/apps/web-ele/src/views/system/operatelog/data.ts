import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';

import { getRangePickerDefaultProps } from '#/utils/range-picker';

/** 操作日志搜索表单 */
export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'UserSelectFormField',
      componentProps: {
        placeholder: '请选择操作人员',
        showDeptFilter: false,
      },
      fieldName: 'userId',
      label: '操作人',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入操作模块',
      },
      fieldName: 'type',
      label: '操作模块',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入操作名',
      },
      fieldName: 'subType',
      label: '操作名',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入操作内容',
      },
      fieldName: 'action',
      label: '操作内容',
    },
    {
      component: 'InputNumber',
      componentProps: {
        clearable: true,
        controls: false,
        min: 0,
        placeholder: '请输入业务编号',
      },
      fieldName: 'bizId',
      label: '业务编号',
    },
    {
      component: 'RangePicker',
      componentProps: {
        ...getRangePickerDefaultProps(),
        clearable: true,
      },
      fieldName: 'createTime',
      label: '操作时间',
    },
  ];
}

/** 操作日志列表字段 */
export function useGridColumns(): VxeTableGridOptions['columns'] {
  return [
    {
      field: 'id',
      minWidth: 100,
      title: '日志编号',
    },
    {
      field: 'userInfo',
      formatter: ({ cellValue }) => {
        return cellValue?.nickname || cellValue?.username || '';
      },
      minWidth: 140,
      title: '操作人',
    },
    {
      field: 'type',
      minWidth: 160,
      title: '操作模块',
    },
    {
      field: 'subType',
      minWidth: 160,
      title: '操作名',
    },
    {
      field: 'action',
      minWidth: 260,
      showOverflow: 'tooltip',
      title: '操作内容',
    },
    {
      field: 'createTime',
      formatter: 'formatDateTime',
      minWidth: 180,
      title: '操作时间',
    },
    {
      field: 'bizId',
      minWidth: 120,
      title: '业务编号',
    },
    {
      field: 'userIp',
      minWidth: 160,
      title: '操作IP',
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
