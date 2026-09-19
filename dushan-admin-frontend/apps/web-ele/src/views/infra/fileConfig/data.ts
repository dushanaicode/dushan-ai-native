import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraFileConfigApi } from '#/api/infra/file-config';

import { DICT_TYPE } from '#/constants/dict-types';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

const ftpModeOptions = [
  { label: '被动模式', value: 'PASV' },
  { label: '主动模式', value: 'PORT' },
];

function isStorage(values: Record<string, unknown>, storages: number[]) {
  return storages.includes(Number(values.storage));
}

/** 新增/编辑表单 */
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
        placeholder: '请输入配置名',
      },
      fieldName: 'name',
      label: '配置名',
      rules: 'required',
    },
    {
      component: 'Select',
      componentProps: {
        options: dictionary.getDictOptions(
          DICT_TYPE.INFRA_FILE_STORAGE,
          'number',
        ),
        placeholder: '请选择存储器',
      },
      dependencies: {
        show: (values) => !values.id,
        triggerFields: ['id'],
      },
      fieldName: 'storage',
      label: '存储器',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入基础路径',
      },
      dependencies: {
        show: (values) => isStorage(values, [10, 11, 12]),
        triggerFields: ['storage'],
      },
      fieldName: 'config.basePath',
      label: '基础路径',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入主机地址',
      },
      dependencies: {
        show: (values) => isStorage(values, [11, 12]),
        triggerFields: ['storage'],
      },
      fieldName: 'config.host',
      label: '主机地址',
      rules: 'required',
    },
    {
      component: 'InputNumber',
      componentProps: {
        controls: false,
        min: 0,
        placeholder: '请输入主机端口',
      },
      dependencies: {
        show: (values) => isStorage(values, [11, 12]),
        triggerFields: ['storage'],
      },
      fieldName: 'config.port',
      label: '主机端口',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入用户名',
      },
      dependencies: {
        show: (values) => isStorage(values, [11, 12]),
        triggerFields: ['storage'],
      },
      fieldName: 'config.username',
      label: '用户名',
      rules: 'required',
    },
    {
      component: 'VbenInputPassword',
      componentProps: {
        placeholder: '请输入密码',
      },
      dependencies: {
        show: (values) => isStorage(values, [11, 12]),
        triggerFields: ['storage'],
      },
      fieldName: 'config.password',
      label: '密码',
      rules: 'required',
    },
    {
      component: 'RadioGroup',
      componentProps: {
        isButton: true,
        options: ftpModeOptions,
      },
      defaultValue: 'PASV',
      dependencies: {
        show: (values) => isStorage(values, [11]),
        triggerFields: ['storage'],
      },
      fieldName: 'config.mode',
      label: '连接模式',
      rules: 'required',
    },
    {
      component: 'Textarea',
      componentProps: {
        placeholder: '请输入 SSH known_hosts 路径或内容',
        rows: 3,
      },
      dependencies: {
        show: (values) => isStorage(values, [12]),
        triggerFields: ['storage'],
      },
      fieldName: 'config.knownHosts',
      label: 'known_hosts',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入节点地址',
      },
      dependencies: {
        show: (values) => isStorage(values, [20]),
        triggerFields: ['storage'],
      },
      fieldName: 'config.endpoint',
      label: '节点地址',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入 Bucket',
      },
      dependencies: {
        show: (values) => isStorage(values, [20]),
        triggerFields: ['storage'],
      },
      fieldName: 'config.bucket',
      label: 'Bucket',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入 Access Key',
      },
      dependencies: {
        show: (values) => isStorage(values, [20]),
        triggerFields: ['storage'],
      },
      fieldName: 'config.accessKey',
      label: 'Access Key',
      rules: 'required',
    },
    {
      component: 'VbenInputPassword',
      componentProps: {
        placeholder: '请输入 Access Secret',
      },
      dependencies: {
        show: (values) => isStorage(values, [20]),
        triggerFields: ['storage'],
      },
      fieldName: 'config.accessSecret',
      label: 'Access Secret',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入 Region，可选',
      },
      dependencies: {
        show: (values) => isStorage(values, [20]),
        triggerFields: ['storage'],
      },
      fieldName: 'config.region',
      label: 'Region',
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
      defaultValue: false,
      dependencies: {
        show: (values) => isStorage(values, [20]),
        triggerFields: ['storage'],
      },
      fieldName: 'config.enablePathStyleAccess',
      label: 'Path Style',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入自定义域名',
      },
      dependencies: {
        show: (values) => Boolean(values.storage),
        triggerFields: ['storage'],
      },
      fieldName: 'config.domain',
      label: '自定义域名',
      rules: 'required',
    },
    {
      component: 'Textarea',
      componentProps: {
        placeholder: '请输入备注',
        rows: 3,
      },
      fieldName: 'remark',
      label: '备注',
    },
  ];
}

/** 搜索表单 */
export function useGridFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入配置名',
      },
      fieldName: 'name',
      label: '配置名',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: dictionary.getDictOptions(
          DICT_TYPE.INFRA_FILE_STORAGE,
          'number',
        ),
        placeholder: '请选择存储器',
      },
      fieldName: 'storage',
      label: '存储器',
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

/** 列表字段 */
export function useGridColumns(): VxeTableGridOptions<InfraFileConfigApi.FileConfigRespVO>['columns'] {
  return [
    { type: 'checkbox', width: 40 },
    {
      field: 'id',
      minWidth: 100,
      title: '编号',
    },
    {
      field: 'name',
      minWidth: 160,
      title: '配置名',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.INFRA_FILE_STORAGE },
      },
      field: 'storage',
      minWidth: 140,
      title: '存储器',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.INFRA_BOOLEAN_STRING },
      },
      field: 'master',
      minWidth: 100,
      title: '主配置',
    },
    {
      field: 'remark',
      minWidth: 180,
      showOverflow: 'tooltip',
      title: '备注',
    },
    {
      field: 'createTime',
      formatter: 'formatDateTime',
      minWidth: 180,
      title: '创建时间',
    },
    {
      align: 'center',
      field: 'operation',
      fixed: 'right',
      slots: { default: 'actions' },
      title: '操作',
      width: 180,
    },
  ];
}
