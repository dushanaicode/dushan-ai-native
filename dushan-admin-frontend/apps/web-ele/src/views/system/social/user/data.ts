import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemSocialUserApi } from '#/api/system/social/user';
import type { DescriptionItemSchema } from '#/components';

import { h } from 'vue';

import { formatDateTime } from '@vben/utils';

import { ElImage } from 'element-plus';

import { DictTag } from '#/components';
import { DICT_TYPE } from '#/constants/dict-types';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

/** 列表的搜索表单 */
export function useGridFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
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
      fieldName: 'type',
      label: '社交平台',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入用户昵称',
      },
      fieldName: 'nickname',
      label: '用户昵称',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入社交 openid',
      },
      fieldName: 'openid',
      label: '社交 openid',
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
export function useGridColumns(): VxeTableGridOptions<SystemSocialUserApi.SocialUserRespVO>['columns'] {
  return [
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.SYSTEM_SOCIAL_TYPE },
      },
      field: 'type',
      minWidth: 130,
      title: '社交平台',
    },
    {
      field: 'openid',
      minWidth: 220,
      showOverflow: 'tooltip',
      title: '社交 openid',
    },
    {
      field: 'nickname',
      minWidth: 140,
      title: '用户昵称',
    },
    {
      cellRender: {
        name: 'CellImage',
        props: {
          fit: 'cover',
          style: 'width: 36px; height: 36px; border-radius: 50%;',
        },
      },
      field: 'avatar',
      title: '用户头像',
      width: 90,
    },
    {
      field: 'createTime',
      formatter: 'formatDateTime',
      minWidth: 180,
      title: '创建时间',
    },
    {
      field: 'updateTime',
      formatter: 'formatDateTime',
      minWidth: 180,
      title: '更新时间',
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

/** 详情页的字段 */
export function useDetailSchema(): DescriptionItemSchema[] {
  return [
    {
      content: (data) =>
        h(DictTag, {
          type: DICT_TYPE.SYSTEM_SOCIAL_TYPE,
          value: data?.type,
        }),
      field: 'type',
      label: '社交平台',
    },
    {
      field: 'nickname',
      label: '用户昵称',
    },
    {
      content: (data) =>
        data?.avatar
          ? h(ElImage, {
              fit: 'cover',
              hideOnClickModal: true,
              previewSrcList: [data.avatar],
              previewTeleported: true,
              src: data.avatar,
              style: 'width: 40px; height: 40px; border-radius: 50%;',
            })
          : '-',
      field: 'avatar',
      label: '用户头像',
    },
    {
      field: 'openid',
      label: '社交 openid',
    },
    {
      content: (data) =>
        data?.createTime ? formatDateTime(data.createTime) : '-',
      field: 'createTime',
      label: '创建时间',
    },
    {
      content: (data) =>
        data?.updateTime ? formatDateTime(data.updateTime) : '-',
      field: 'updateTime',
      label: '更新时间',
    },
  ];
}
