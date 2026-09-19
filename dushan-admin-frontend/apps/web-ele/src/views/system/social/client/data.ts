import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemSocialClientApi } from '#/api/system/social/client';

import { z } from '#/adapter/form';
import { DICT_TYPE } from '#/constants/dict-types';
import { SystemUserSocialTypeEnum } from '#/constants/enums';
import { SwitchStatus } from '#/constants/status';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

function isWechatEnterprise(values: Record<string, any>) {
  return (
    values.socialType === SystemUserSocialTypeEnum.WECHAT_ENTERPRISE.type ||
    values.socialType === SystemUserSocialTypeEnum.WECHAT_ENTERPRISE_v2.type
  );
}

/** 新增/修改的表单 */
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
        clearable: true,
        maxlength: 255,
        placeholder: '请输入应用名',
        showWordLimit: true,
      },
      fieldName: 'name',
      label: '应用名',
      rules: 'required',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.SYSTEM_SOCIAL_TYPE,
          'number',
        ),
        placeholder: '请选择社交平台',
      },
      fieldName: 'socialType',
      label: '社交平台',
      rules: z.number(),
    },
    {
      component: 'RadioGroup',
      componentProps: {
        isButton: true,
        options: dictionary.getDictOptions(DICT_TYPE.USER_TYPE, 'number'),
      },
      fieldName: 'userType',
      label: '用户类型',
      rules: z.number(),
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        maxlength: 255,
        placeholder: '请输入客户端编号，对应各平台的 appKey',
        showWordLimit: true,
      },
      fieldName: 'clientId',
      label: '客户端编号',
      rules: 'required',
    },
    {
      component: 'VbenInputPassword',
      componentProps: {
        maxlength: 32_768,
        placeholder: '请输入客户端密钥或平台私钥',
      },
      fieldName: 'clientSecret',
      label: '密钥 / 私钥',
      rules: z.string().min(1, '请输入客户端密钥或平台私钥'),
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        maxlength: 255,
        placeholder: '请输入授权方的网页应用编号',
        showWordLimit: true,
      },
      dependencies: {
        rules: (values) =>
          isWechatEnterprise(values)
            ? z.string().min(1, '请输入授权方的网页应用编号')
            : z.string().optional(),
        show: isWechatEnterprise,
        triggerFields: ['socialType'],
      },
      fieldName: 'agentId',
      label: 'Agent ID',
    },
    {
      component: 'RadioGroup',
      componentProps: {
        isButton: true,
        options: dictionary.getDictOptions(DICT_TYPE.COMMON_STATUS, 'number'),
      },
      fieldName: 'status',
      label: '状态',
      rules: z.number().default(SwitchStatus.DISABLED),
    },
    {
      component: 'Textarea',
      componentProps: {
        clearable: true,
        placeholder:
          '请输入认证配置 JSON；支付宝需 alipayPublicKey，启用时需 redirectUri',
        rows: 5,
      },
      fieldName: 'authConfigJson',
      formItemClass: 'col-span-2',
      label: '认证配置',
    },
  ];
}

/** 列表的搜索表单 */
export function useGridFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入应用名',
      },
      fieldName: 'name',
      label: '应用名',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.SYSTEM_SOCIAL_TYPE,
          'number',
        ),
        placeholder: '请选择社交平台',
      },
      fieldName: 'socialType',
      label: '社交平台',
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

/** 列表的字段 */
export function useGridColumns(
  onStatusChange?: (
    newStatus: number,
    row: SystemSocialClientApi.SocialClientRespVO,
  ) => Promise<boolean | undefined>,
): VxeTableGridOptions<SystemSocialClientApi.SocialClientRespVO>['columns'] {
  return [
    { fixed: 'left', type: 'checkbox', width: 40 },
    {
      field: 'id',
      minWidth: 90,
      title: '编号',
    },
    {
      field: 'name',
      minWidth: 150,
      title: '应用名',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.SYSTEM_SOCIAL_TYPE },
      },
      field: 'socialType',
      minWidth: 130,
      title: '社交平台',
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
      field: 'agentId',
      minWidth: 120,
      showOverflow: 'tooltip',
      title: 'Agent ID',
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
      minWidth: 130,
      slots: { default: 'actions' },
      title: '操作',
    },
  ];
}
