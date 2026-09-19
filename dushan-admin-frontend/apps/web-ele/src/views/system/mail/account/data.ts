import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemMailAccountApi } from '#/api/system/mail/account';

import { z } from '#/adapter/form';
import { DICT_TYPE } from '#/constants/dict-types';

function requiredString(message: string) {
  return z.string().min(1, message);
}

/** 新增/修改的表单 */
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
        clearable: true,
        placeholder: '请输入邮箱',
      },
      fieldName: 'mail',
      label: '邮箱',
      rules: requiredString('请输入邮箱').email('请输入正确的邮箱地址'),
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入用户名',
      },
      fieldName: 'username',
      label: '用户名',
      rules: 'required',
    },
    {
      component: 'VbenInputPassword',
      componentProps: {
        placeholder: '请输入密码',
      },
      fieldName: 'password',
      label: '密码',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入 SMTP 服务器域名',
      },
      fieldName: 'host',
      label: 'SMTP 服务器',
      rules: 'required',
    },
    {
      component: 'InputNumber',
      componentProps: {
        max: 65_535,
        min: 0,
        placeholder: '请输入 SMTP 服务器端口',
      },
      fieldName: 'port',
      label: 'SMTP 端口',
      rules: 'required',
    },
    {
      component: 'Switch',
      fieldName: 'sslEnable',
      label: '开启 SSL',
      rules: z.boolean().default(true),
    },
    {
      component: 'Switch',
      fieldName: 'starttlsEnable',
      label: '开启 STARTTLS',
      rules: z.boolean().default(false),
    },
  ];
}

/** 列表的搜索表单 */
export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入邮箱',
      },
      fieldName: 'mail',
      label: '邮箱',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入用户名',
      },
      fieldName: 'username',
      label: '用户名',
    },
  ];
}

/** 列表的字段 */
export function useGridColumns(): VxeTableGridOptions<SystemMailAccountApi.MailAccountRespVO>['columns'] {
  return [
    { fixed: 'left', type: 'checkbox', width: 40 },
    {
      field: 'id',
      minWidth: 100,
      title: '编号',
    },
    {
      field: 'mail',
      minWidth: 180,
      title: '邮箱',
    },
    {
      field: 'username',
      minWidth: 140,
      title: '用户名',
    },
    {
      field: 'host',
      minWidth: 180,
      title: 'SMTP 服务器',
    },
    {
      field: 'port',
      minWidth: 110,
      title: 'SMTP 端口',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.INFRA_BOOLEAN_STRING },
      },
      field: 'sslEnable',
      minWidth: 110,
      title: '开启 SSL',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.INFRA_BOOLEAN_STRING },
      },
      field: 'starttlsEnable',
      minWidth: 140,
      title: '开启 STARTTLS',
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
      minWidth: 130,
      slots: { default: 'actions' },
      title: '操作',
    },
  ];
}
