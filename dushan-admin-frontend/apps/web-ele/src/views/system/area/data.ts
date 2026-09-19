import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemAreaApi } from '#/api/system/area';

/** IP 查询表单 */
export function useFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入 IP 地址',
      },
      fieldName: 'ip',
      label: 'IP 地址',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '展示查询 IP 结果',
        readonly: true,
      },
      fieldName: 'result',
      label: '地址',
    },
  ];
}

/** 地区树表字段 */
export function useGridColumns(): VxeTableGridOptions<SystemAreaApi.AreaNodeRespVO>['columns'] {
  return [
    {
      align: 'left',
      field: 'id',
      fixed: 'left',
      minWidth: 140,
      title: '地区编码',
      treeNode: true,
    },
    {
      align: 'left',
      field: 'name',
      minWidth: 220,
      title: '地区名称',
    },
  ];
}
