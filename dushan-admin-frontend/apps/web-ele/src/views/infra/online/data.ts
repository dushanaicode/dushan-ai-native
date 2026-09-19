import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraOnlineApi } from '#/api/infra/online';

export const ONLINE_QUERY_PERMISSION = 'infra:online:list';
export const ONLINE_FORCE_LOGOUT_PERMISSION = 'infra:online:force-logout';

/** 列表的搜索表单 */
export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入登录地址',
      },
      fieldName: 'ipaddr',
      label: '登录地址',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入用户名',
      },
      fieldName: 'userName',
      label: '用户名',
    },
  ];
}

/** 列表的字段 */
export function useGridColumns(): VxeTableGridOptions<InfraOnlineApi.OnlineInfoRespVO>['columns'] {
  return [
    {
      title: '序号',
      type: 'seq',
      width: 60,
    },
    {
      field: 'tokenId',
      minWidth: 180,
      showOverflow: 'tooltip',
      title: '会话编号',
    },
    {
      field: 'userName',
      minWidth: 120,
      showOverflow: 'tooltip',
      title: '登录名称',
    },
    {
      field: 'deptName',
      minWidth: 120,
      showOverflow: 'tooltip',
      title: '所属部门',
    },
    {
      field: 'ipaddr',
      minWidth: 140,
      showOverflow: 'tooltip',
      title: '主机',
    },
    {
      field: 'loginLocation',
      minWidth: 140,
      showOverflow: 'tooltip',
      title: '登录地点',
    },
    {
      field: 'os',
      minWidth: 140,
      showOverflow: 'tooltip',
      title: '操作系统',
    },
    {
      field: 'browser',
      minWidth: 120,
      showOverflow: 'tooltip',
      title: '浏览器',
    },
    {
      field: 'loginTime',
      formatter: 'formatDateTime',
      minWidth: 180,
      title: '登录时间',
    },
    {
      align: 'center',
      field: 'operation',
      fixed: 'right',
      slots: { default: 'actions' },
      title: '操作',
      width: 120,
    },
  ];
}
