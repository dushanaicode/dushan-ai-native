import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemOAuth2TokenApi } from '#/api/system/oauth2/token';

import { DICT_TYPE } from '#/constants/dict-types';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

/** 列表的搜索表单 */
export function useGridFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
    {
      component: 'InputNumber',
      componentProps: {
        min: 1,
        placeholder: '请输入用户编号',
      },
      fieldName: 'userId',
      label: '用户编号',
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
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入客户端编号',
      },
      fieldName: 'clientId',
      label: '客户端编号',
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

/** 列表的字段 */
export function useGridColumns(): VxeTableGridOptions<SystemOAuth2TokenApi.OAuth2AccessTokenRespVO>['columns'] {
  return [
    { fixed: 'left', type: 'checkbox', width: 40 },
    {
      field: 'id',
      minWidth: 90,
      title: '编号',
    },
    {
      field: 'familyId',
      minWidth: 260,
      showOverflow: 'tooltip',
      title: '令牌族',
    },
    {
      field: 'refreshTokenId',
      minWidth: 260,
      showOverflow: 'tooltip',
      title: '刷新令牌编号',
    },
    {
      field: 'userId',
      minWidth: 110,
      title: '用户编号',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.USER_TYPE },
      },
      field: 'userType',
      minWidth: 110,
      title: '用户类型',
    },
    {
      field: 'clientId',
      minWidth: 180,
      showOverflow: 'tooltip',
      title: '客户端编号',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.INFRA_BOOLEAN_STRING },
      },
      field: 'revoked',
      minWidth: 90,
      title: '已吊销',
    },
    {
      field: 'expiresTime',
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
      minWidth: 90,
      slots: { default: 'actions' },
      title: '操作',
    },
  ];
}
