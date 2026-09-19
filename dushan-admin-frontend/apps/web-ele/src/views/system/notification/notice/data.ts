import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemDeptApi } from '#/api/system/dept';
import type { SystemNoticeApi } from '#/api/system/notification/notice';

import { z } from '#/adapter/form';
import { getSimpleDeptList } from '#/api/system/dept';
import { getSimpleMailAccountList } from '#/api/system/mail/account';
import { getSimpleSmsTemplateList } from '#/api/system/sms/template';
import { DICT_TYPE } from '#/constants/dict-types';
import { SwitchStatus } from '#/constants/status';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

interface DeptTreeNode extends SystemDeptApi.DeptSimpleRespVO {
  children?: DeptTreeNode[];
}

function buildDeptTree(list: SystemDeptApi.DeptSimpleRespVO[]): DeptTreeNode[] {
  const nodeMap = new Map<string, DeptTreeNode>();
  const roots: DeptTreeNode[] = [];

  for (const item of list) {
    nodeMap.set(item.id, { ...item });
  }

  for (const item of list) {
    const node = nodeMap.get(item.id);
    if (!node) continue;

    const parentId = item.parentId ?? '0';
    const parentNode = nodeMap.get(parentId);
    if (parentId !== '0' && parentNode) {
      parentNode.children ||= [];
      parentNode.children.push(node);
    } else {
      roots.push(node);
    }
  }

  return roots;
}

function hasChannel(values: Record<string, any>, channel: string) {
  return Array.isArray(values.channels) && values.channels.includes(channel);
}

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
        maxlength: 50,
        placeholder: '请输入通知标题',
        showWordLimit: true,
      },
      fieldName: 'title',
      label: '通知标题',
      rules: 'required',
    },
    {
      component: 'Select',
      componentProps: {
        options: dictionary.getDictOptions(
          DICT_TYPE.SYSTEM_NOTICE_TYPE,
          'number',
        ),
        placeholder: '请选择通知类型',
      },
      fieldName: 'type',
      label: '通知类型',
      rules: 'selectRequired',
    },
    {
      component: 'Select',
      componentProps: {
        options: dictionary.getDictOptions(DICT_TYPE.USER_TYPE, 'number'),
        placeholder: '请选择用户类型',
      },
      fieldName: 'userType',
      label: '用户类型',
      rules: 'selectRequired',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        collapseTags: true,
        multiple: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.SYSTEM_NOTIFICATION_CHANNEL,
          'string',
        ),
        placeholder: '请选择推送渠道',
      },
      fieldName: 'channels',
      label: '推送渠道',
      rules: z.array(z.string()).min(1, '请选择推送渠道'),
    },
    {
      component: 'ApiSelect',
      componentProps: {
        api: getSimpleSmsTemplateList,
        clearable: true,
        labelField: 'name',
        placeholder: '请选择短信模板',
        valueField: 'code',
      },
      dependencies: {
        rules: (values) =>
          hasChannel(values, 'SMS')
            ? requiredString('请选择短信模板')
            : z.string().optional(),
        show: (values) => hasChannel(values, 'SMS'),
        triggerFields: ['channels'],
      },
      fieldName: 'smsTemplateCode',
      label: '短信模板',
    },
    {
      component: 'ApiSelect',
      componentProps: {
        api: getSimpleMailAccountList,
        clearable: true,
        labelField: 'mail',
        placeholder: '请选择邮箱账号',
        valueField: 'id',
      },
      dependencies: {
        rules: (values) =>
          hasChannel(values, 'MAIL')
            ? requiredString('请选择邮箱账号')
            : z.string().optional(),
        show: (values) => hasChannel(values, 'MAIL'),
        triggerFields: ['channels'],
      },
      fieldName: 'mailAccountId',
      label: '邮箱账号',
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
      component: 'RadioGroup',
      componentProps: {
        isButton: true,
        options: dictionary.getDictOptions(DICT_TYPE.COMMON_STATUS, 'number'),
      },
      fieldName: 'status',
      label: '状态',
      rules: z.number().default(SwitchStatus.ENABLED),
    },
    {
      component: 'RichTextarea',
      componentProps: {
        imageDirectory: 'notice',
        minHeight: 260,
        placeholder: '请输入通知内容',
      },
      fieldName: 'content',
      formItemClass: 'col-span-2',
      label: '通知内容',
      rules: requiredString('请输入通知内容'),
    },
  ];
}

export function usePushTargetFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'ApiTreeSelect',
      componentProps: {
        api: async () => {
          const data = await getSimpleDeptList();
          return buildDeptTree(data);
        },
        checkStrictly: true,
        childrenField: 'children',
        clearable: true,
        collapseTags: true,
        labelField: 'name',
        multiple: true,
        nodeKey: 'id',
        placeholder: '请选择目标部门',
        props: { label: 'name', children: 'children' },
        showCheckbox: true,
        treeDefaultExpandAll: true,
        valueField: 'id',
      },
      fieldName: 'deptIds',
      label: '目标部门',
    },
    {
      component: 'UserSelectFormField',
      componentProps: {
        multiple: true,
        placeholder: '请选择目标用户',
        showDeptFilter: true,
      },
      fieldName: 'userIds',
      label: '目标用户',
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
        placeholder: '请输入通知标题',
      },
      fieldName: 'title',
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
      fieldName: 'type',
      label: '通知类型',
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
      component: 'Select',
      componentProps: {
        clearable: true,
        collapseTags: true,
        multiple: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.SYSTEM_NOTIFICATION_CHANNEL,
          'string',
        ),
        placeholder: '请选择推送渠道',
      },
      fieldName: 'channels',
      label: '推送渠道',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入发布人',
      },
      fieldName: 'publisher',
      label: '发布人',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(DICT_TYPE.COMMON_STATUS, 'number'),
        placeholder: '请选择状态',
      },
      fieldName: 'status',
      label: '状态',
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

export function useGridColumns(
  onStatusChange?: (
    newStatus: number,
    row: SystemNoticeApi.NoticeRespVO,
  ) => Promise<boolean | undefined>,
): VxeTableGridOptions<SystemNoticeApi.NoticeRespVO>['columns'] {
  return [
    { fixed: 'left', type: 'checkbox', width: 40 },
    {
      field: 'id',
      minWidth: 100,
      title: '通知编号',
    },
    {
      field: 'title',
      minWidth: 220,
      showOverflow: 'tooltip',
      title: '通知标题',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.COMMON_BUILTIN_TYPE },
      },
      field: 'builtin',
      minWidth: 100,
      title: '内置类型',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.SYSTEM_NOTICE_TYPE },
      },
      field: 'type',
      minWidth: 100,
      title: '通知类型',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.USER_TYPE },
      },
      field: 'userType',
      minWidth: 100,
      title: '用户类型',
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
      field: 'channels',
      minWidth: 180,
      title: '推送渠道',
    },
    {
      field: 'publisher',
      minWidth: 120,
      title: '发布人',
    },
    {
      align: 'center',
      cellRender: {
        attrs: { beforeChange: onStatusChange },
        name: 'CellSwitch',
        props: {
          checkedValue: SwitchStatus.ENABLED,
          unCheckedValue: SwitchStatus.DISABLED,
        },
      },
      field: 'status',
      title: '状态',
      width: 90,
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
      minWidth: 250,
      slots: { default: 'actions' },
      title: '操作',
    },
  ];
}
