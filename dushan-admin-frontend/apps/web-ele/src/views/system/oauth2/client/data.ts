import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemOAuth2ClientApi } from '#/api/system/oauth2/client';

import { z } from '#/adapter/form';
import { DICT_TYPE } from '#/constants/dict-types';
import { UserTypeEnum } from '#/constants/enums';
import { SwitchStatus } from '#/constants/status';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

function useTagSelectProps(placeholder: string) {
  return {
    allowCreate: true,
    clearable: true,
    collapseTags: true,
    collapseTagsTooltip: true,
    filterable: true,
    multiple: true,
    placeholder,
  };
}

function formatStringList(value: unknown) {
  return Array.isArray(value) && value.length > 0 ? value.join(', ') : '-';
}

const strongClientSecretSchema = z
  .string()
  .min(32, '客户端密钥至少需要 32 位')
  .max(255, '客户端密钥不能超过 255 位')
  .regex(/^[!-~]+$/, '客户端密钥只能包含无空白 ASCII 可打印字符')
  .refine(
    (value) =>
      [/[a-z]/, /[A-Z]/, /\d/, /[^A-Za-z0-9]/].filter((pattern) =>
        pattern.test(value),
      ).length >= 3,
    '客户端密钥必须至少包含三类大小写字母、数字或符号',
  );

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
        placeholder: '请输入客户端编号',
        showWordLimit: true,
      },
      fieldName: 'clientId',
      label: '客户端编号',
      rules: 'required',
    },
    {
      component: 'VbenInputPassword',
      componentProps: {
        maxlength: 255,
        placeholder: '创建时必填；编辑留空保持不变，填写则轮换密钥',
      },
      dependencies: {
        rules: (values) =>
          values.id
            ? z.union([strongClientSecretSchema, z.literal('')]).optional()
            : strongClientSecretSchema,
        triggerFields: ['id'],
      },
      fieldName: 'secret',
      label: '客户端密钥',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        maxlength: 255,
        placeholder: '请输入客户端名称',
        showWordLimit: true,
      },
      fieldName: 'name',
      label: '客户端名称',
      rules: 'required',
    },
    {
      component: 'ImageUpload',
      componentProps: {
        directory: 'oauth2/client',
        helpText: '支持 jpg/png/webp，建议使用正方形图片',
        maxNumber: 1,
      },
      fieldName: 'logo',
      label: '客户端图标',
      rules: 'required',
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
      component: 'RadioGroup',
      componentProps: {
        isButton: true,
        options: dictionary.getDictOptions(DICT_TYPE.USER_TYPE, 'number'),
      },
      fieldName: 'userType',
      label: '主体类型',
      rules: z.number().default(UserTypeEnum.ADMIN),
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: 1,
        placeholder: '请输入访问令牌有效期',
      },
      fieldName: 'accessTokenValiditySeconds',
      label: '访问令牌有效期',
      rules: 'required',
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: 1,
        placeholder: '请输入刷新令牌有效期',
      },
      fieldName: 'refreshTokenValiditySeconds',
      label: '刷新令牌有效期',
      rules: 'required',
    },
    {
      component: 'Select',
      componentProps: {
        ...useTagSelectProps('请输入授权重定向地址'),
      },
      fieldName: 'redirectUris',
      formItemClass: 'col-span-2',
      label: '重定向地址',
      rules: z.array(z.string()).min(1, '请输入重定向地址'),
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        collapseTags: true,
        collapseTagsTooltip: true,
        multiple: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.SYSTEM_OAUTH2_GRANT_TYPE,
          'string',
        ),
        placeholder: '请选择授权类型',
      },
      fieldName: 'authorizedGrantTypes',
      formItemClass: 'col-span-2',
      label: '授权类型',
      rules: z.array(z.string()).min(1, '请选择授权类型'),
    },
    {
      component: 'Select',
      componentProps: {
        ...useTagSelectProps('请输入授权范围'),
      },
      fieldName: 'scopes',
      label: '授权范围',
    },
    {
      component: 'Select',
      componentProps: {
        ...useTagSelectProps('请输入自动授权范围'),
      },
      fieldName: 'autoApproveScopes',
      label: '自动授权范围',
    },
    {
      component: 'Select',
      componentProps: {
        ...useTagSelectProps('请输入权限'),
      },
      fieldName: 'authorities',
      label: '权限',
    },
    {
      component: 'Select',
      componentProps: {
        ...useTagSelectProps('请输入资源编号'),
      },
      fieldName: 'resourceIds',
      label: '资源编号',
    },
    {
      component: 'Textarea',
      componentProps: {
        clearable: true,
        maxlength: 255,
        placeholder: '请输入客户端描述',
        rows: 3,
        showWordLimit: true,
      },
      fieldName: 'description',
      formItemClass: 'col-span-2',
      label: '客户端描述',
    },
    {
      component: 'Textarea',
      componentProps: {
        clearable: true,
        placeholder: '请输入附加信息 JSON',
        rows: 4,
      },
      fieldName: 'additionalInformation',
      formItemClass: 'col-span-2',
      label: '附加信息',
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
        placeholder: '请输入客户端名称',
      },
      fieldName: 'name',
      label: '客户端名称',
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
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(DICT_TYPE.USER_TYPE, 'number'),
        placeholder: '请选择主体类型',
      },
      fieldName: 'userType',
      label: '主体类型',
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
    row: SystemOAuth2ClientApi.OAuth2ClientRespVO,
  ) => Promise<boolean | undefined>,
): VxeTableGridOptions<SystemOAuth2ClientApi.OAuth2ClientRespVO>['columns'] {
  return [
    { fixed: 'left', type: 'checkbox', width: 40 },
    {
      field: 'id',
      minWidth: 90,
      title: '编号',
    },
    {
      field: 'clientId',
      minWidth: 180,
      showOverflow: 'tooltip',
      title: '客户端编号',
    },
    {
      field: 'name',
      minWidth: 160,
      title: '客户端名称',
    },
    {
      cellRender: {
        name: 'CellImage',
        props: {
          fit: 'cover',
          style: 'width: 36px; height: 36px; border-radius: 6px;',
        },
      },
      field: 'logo',
      title: '图标',
      width: 80,
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
      cellRender: {
        name: 'CellDict',
        props: {
          type: DICT_TYPE.USER_TYPE,
        },
      },
      field: 'userType',
      title: '主体类型',
      width: 100,
    },
    {
      cellRender: {
        name: 'CellDict',
        props: {
          multiple: true,
          noWrap: true,
          type: DICT_TYPE.SYSTEM_OAUTH2_GRANT_TYPE,
        },
      },
      field: 'authorizedGrantTypes',
      minWidth: 240,
      title: '授权类型',
    },
    {
      field: 'redirectUris',
      formatter: ({ cellValue }) => formatStringList(cellValue),
      minWidth: 260,
      showOverflow: 'tooltip',
      title: '重定向地址',
    },
    {
      field: 'accessTokenValiditySeconds',
      minWidth: 130,
      title: '访问令牌有效期',
    },
    {
      field: 'refreshTokenValiditySeconds',
      minWidth: 130,
      title: '刷新令牌有效期',
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
