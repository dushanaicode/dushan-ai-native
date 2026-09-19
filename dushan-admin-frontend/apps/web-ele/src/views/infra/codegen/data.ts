import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { InfraCodegenApi } from '#/api/infra/codegen';
import type { SystemMenuApi } from '#/api/system/menu';

import { z } from '#/adapter/form';
import { getDataSourceConfigListByStatus } from '#/api/infra/data-source-config';
import { getMenuList } from '#/api/system/menu';
import { DICT_TYPE } from '#/constants/dict-types';
import { InfraCodegenTemplateTypeEnum } from '#/constants/enums';
import { SwitchStatus } from '#/constants/status';
import { useDictionary } from '#/services/dictionary/context';
import { getRangePickerDefaultProps } from '#/utils/range-picker';

interface MenuTreeNode extends SystemMenuApi.MenuRespVO {
  children?: MenuTreeNode[];
  disabled?: boolean;
}

const pythonTypeOptions = [
  { label: 'int', value: 'int' },
  { label: 'str', value: 'str' },
  { label: 'float', value: 'float' },
  { label: 'Decimal', value: 'Decimal' },
  { label: 'bool', value: 'bool' },
  { label: 'datetime', value: 'datetime' },
  { label: 'bytes', value: 'bytes' },
];

const listConditionOptions = [
  { label: '=', value: '=' },
  { label: '!=', value: '!=' },
  { label: '>', value: '>' },
  { label: '>=', value: '>=' },
  { label: '<', value: '<' },
  { label: '<=', value: '<=' },
  { label: 'LIKE', value: 'LIKE' },
  { label: 'BETWEEN', value: 'BETWEEN' },
];

const htmlTypeOptions = [
  { label: '文本框', value: 'input' },
  { label: '文本域', value: 'textarea' },
  { label: '下拉框', value: 'select' },
  { label: '单选框', value: 'radio' },
  { label: '复选框', value: 'checkbox' },
  { label: '日期控件', value: 'datetime' },
  { label: '图片上传', value: 'imageUpload' },
  { label: '文件上传', value: 'fileUpload' },
  { label: '富文本控件', value: 'editor' },
];

const subJoinExcludeFields = new Set([
  'create_time',
  'creator',
  'deleted',
  'id',
  'update_time',
  'updater',
]);

function buildMenuTree(list: SystemMenuApi.MenuRespVO[]): MenuTreeNode[] {
  const nodeMap = new Map<string, MenuTreeNode>();
  const roots: MenuTreeNode[] = [];

  for (const item of list) {
    nodeMap.set(item.id, {
      ...item,
      disabled: item.kind === 'action',
    });
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

function columnOptions(columns: InfraCodegenApi.CodegenColumnRespVO[] = []) {
  return columns.map((column) => ({
    label: `${column.columnName}：${column.columnComment}`,
    value: column.id,
  }));
}

function requiredString(message: string) {
  return z.string().min(1, message);
}

function requiredPatternString(
  message: string,
  pattern: RegExp,
  patternMessage: string,
) {
  return requiredString(message).regex(pattern, patternMessage);
}

/** 列表搜索表单 */
export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入表名称',
      },
      fieldName: 'tableName',
      label: '表名称',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入表描述',
      },
      fieldName: 'tableComment',
      label: '表描述',
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
export function useGridColumns(
  getDataSourceConfigName?: (dataSourceConfigId: string) => string | undefined,
): VxeTableGridOptions<InfraCodegenApi.CodegenTableRespVO>['columns'] {
  return [
    { fixed: 'left', type: 'checkbox', width: 40 },
    {
      field: 'dataSourceConfigId',
      formatter: ({ cellValue }) =>
        getDataSourceConfigName?.(String(cellValue ?? '')) || '-',
      minWidth: 140,
      title: '数据源',
    },
    {
      field: 'tableName',
      fixed: 'left',
      minWidth: 180,
      showOverflow: 'tooltip',
      title: '表名称',
    },
    {
      field: 'tableComment',
      minWidth: 180,
      showOverflow: 'tooltip',
      title: '表描述',
    },
    {
      field: 'className',
      minWidth: 180,
      showOverflow: 'tooltip',
      title: '实体类',
    },
    {
      cellRender: {
        name: 'CellDict',
        props: { type: DICT_TYPE.INFRA_CODEGEN_TEMPLATE_TYPE },
      },
      field: 'templateType',
      minWidth: 120,
      title: '模板',
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
      minWidth: 300,
      slots: { default: 'actions' },
      title: '操作',
    },
  ];
}

/** 导入数据库表搜索表单 */
export function useImportTableFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'ApiSelect',
      componentProps: {
        api: () => getDataSourceConfigListByStatus(SwitchStatus.ENABLED),
        autoSelect: 'first',
        clearable: true,
        labelField: 'name',
        placeholder: '请选择数据源',
        valueField: 'id',
      },
      fieldName: 'dataSourceConfigId',
      label: '数据源',
      rules: 'selectRequired',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入表名称',
      },
      fieldName: 'tableName',
      label: '表名称',
    },
    {
      component: 'Input',
      componentProps: {
        clearable: true,
        placeholder: '请输入表描述',
      },
      fieldName: 'tableComment',
      label: '表描述',
    },
  ];
}

/** 导入数据库表字段 */
export function useImportTableColumns(): VxeTableGridOptions<InfraCodegenApi.DatabaseTableRespVO>['columns'] {
  return [
    { type: 'checkbox', width: 40 },
    {
      field: 'name',
      minWidth: 220,
      title: '表名称',
    },
    {
      field: 'comment',
      minWidth: 260,
      showOverflow: 'tooltip',
      title: '表描述',
    },
  ];
}

/** 基本信息表单 */
export function useBasicInfoFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入表名称',
      },
      fieldName: 'tableName',
      label: '表名称',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入表描述',
      },
      fieldName: 'tableComment',
      label: '表描述',
      rules: 'required',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入实体类名称',
      },
      fieldName: 'className',
      label: '实体类名称',
      rules: requiredPatternString(
        '请输入实体类名称',
        /^[A-Z][A-Za-z0-9]*$/,
        '实体类名称必须是 PascalCase，例如 DemoUser',
      ),
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入作者',
      },
      fieldName: 'author',
      label: '作者',
      rules: 'required',
    },
    {
      component: 'Textarea',
      componentProps: {
        placeholder: '请输入备注',
        rows: 3,
      },
      fieldName: 'remark',
      formItemClass: 'col-span-2',
      label: '备注',
    },
  ];
}

/** 生成信息基础表单 */
export function useGenerationInfoBaseFormSchema(): VbenFormSchema[] {
  const dictionary = useDictionary();
  return [
    {
      component: 'Select',
      componentProps: {
        options: dictionary.getDictOptions(
          DICT_TYPE.INFRA_CODEGEN_TEMPLATE_TYPE,
          'number',
        ),
        placeholder: '请选择生成模板',
      },
      fieldName: 'templateType',
      label: '生成模板',
      rules: z.number().default(InfraCodegenTemplateTypeEnum.CRUD),
    },
    {
      component: 'Select',
      componentProps: {
        options: dictionary.getDictOptions(
          DICT_TYPE.INFRA_CODEGEN_FRONT_TYPE,
          'number',
        ),
        placeholder: '请选择前端类型',
      },
      fieldName: 'frontType',
      label: '前端类型',
      rules: 'selectRequired',
    },
    {
      component: 'Select',
      componentProps: {
        options: dictionary.getDictOptions(
          DICT_TYPE.INFRA_CODEGEN_SCENE,
          'number',
        ),
        placeholder: '请选择生成场景',
      },
      fieldName: 'scene',
      label: '生成场景',
      rules: 'selectRequired',
    },
    {
      component: 'ApiTreeSelect',
      componentProps: {
        api: async () => {
          const data = await getMenuList();
          return [
            {
              children: buildMenuTree(data),
              id: '0',
              kind: 'group',
              name: '顶级菜单',
              parentId: '0',
            },
          ];
        },
        checkStrictly: true,
        childrenField: 'children',
        clearable: true,
        labelField: 'name',
        nodeKey: 'id',
        placeholder: '请选择上级菜单',
        props: { label: 'name', children: 'children', disabled: 'disabled' },
        treeDefaultExpandAll: true,
        valueField: 'id',
      },
      fieldName: 'parentMenuId',
      label: '上级菜单',
      rules: 'selectRequired',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入模块名，例如 infra',
      },
      fieldName: 'moduleName',
      label: '模块名',
      rules: requiredPatternString(
        '请输入模块名',
        /^[a-z][a-z0-9_]*$/,
        '模块名只能使用小写字母、数字和下划线，且必须以小写字母开头',
      ),
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入业务名，例如 codegen 或 demo_user',
      },
      fieldName: 'businessName',
      label: '业务名',
      rules: requiredPatternString(
        '请输入业务名',
        /^[a-z][a-z0-9_]*$/,
        '业务名只能使用小写字母、数字和下划线，且必须以小写字母开头',
      ),
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '请输入类描述',
      },
      fieldName: 'classComment',
      label: '类描述',
      rules: requiredString('请输入类描述'),
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
      fieldName: 'enableExport',
      label: '启用导出',
      rules: z.boolean().default(true),
    },
  ];
}

/** 树表生成信息 */
export function useGenerationInfoTreeFormSchema(
  columns: InfraCodegenApi.CodegenColumnRespVO[] = [],
): VbenFormSchema[] {
  return [
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: columnOptions(columns),
        placeholder: '请选择父编号字段',
      },
      fieldName: 'treeParentColumnId',
      label: '父编号字段',
      rules: 'selectRequired',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: columnOptions(columns),
        placeholder: '请选择名称字段',
      },
      fieldName: 'treeNameColumnId',
      label: '名称字段',
      rules: 'selectRequired',
    },
  ];
}

/** 主子表生成信息 */
export function useGenerationInfoSubTableFormSchema(
  columns: InfraCodegenApi.CodegenColumnRespVO[] = [],
  tables: InfraCodegenApi.CodegenTableRespVO[] = [],
  currentTableId?: string,
): VbenFormSchema[] {
  const filteredTables = currentTableId
    ? tables.filter((table) => table.id !== currentTableId)
    : tables;
  const filteredColumns = columns.filter(
    (column) => !subJoinExcludeFields.has(column.columnName),
  );

  return [
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: filteredTables.map((table) => ({
          label: `${table.tableName}：${table.tableComment}`,
          value: table.id,
        })),
        placeholder: '请选择关联主表',
      },
      fieldName: 'masterTableId',
      label: '关联主表',
      rules: 'selectRequired',
    },
    {
      component: 'Select',
      componentProps: {
        clearable: true,
        options: columnOptions(filteredColumns),
        placeholder: '请选择子表关联字段',
      },
      fieldName: 'subJoinColumnId',
      label: '关联字段',
      rules: 'selectRequired',
    },
    {
      component: 'RadioGroup',
      componentProps: {
        isButton: true,
        options: [
          { label: '一对多', value: true },
          { label: '一对一', value: false },
        ],
      },
      fieldName: 'subJoinMany',
      label: '关联关系',
      rules: z.boolean().default(true),
    },
  ];
}

/** 字段配置表格 */
export function useCodegenColumnTableColumns(): VxeTableGridOptions<InfraCodegenApi.CodegenColumnRespVO>['columns'] {
  return [
    { field: 'columnName', fixed: 'left', minWidth: 140, title: '字段列名' },
    {
      field: 'columnComment',
      minWidth: 140,
      slots: { default: 'columnComment' },
      title: '字段描述',
    },
    { field: 'dataType', minWidth: 110, title: '物理类型' },
    {
      field: 'fieldType',
      minWidth: 130,
      params: { options: pythonTypeOptions },
      slots: { default: 'fieldType' },
      title: 'Python 类型',
    },
    {
      field: 'fieldName',
      minWidth: 130,
      slots: { default: 'fieldName' },
      title: 'Python 属性',
    },
    {
      align: 'center',
      field: 'createOperation',
      slots: { default: 'createOperation' },
      title: '插入',
      width: 70,
    },
    {
      align: 'center',
      field: 'updateOperation',
      slots: { default: 'updateOperation' },
      title: '编辑',
      width: 70,
    },
    {
      align: 'center',
      field: 'listOperationResult',
      slots: { default: 'listOperationResult' },
      title: '列表',
      width: 70,
    },
    {
      align: 'center',
      field: 'listOperation',
      slots: { default: 'listOperation' },
      title: '查询',
      width: 70,
    },
    {
      field: 'listOperationCondition',
      minWidth: 120,
      params: { options: listConditionOptions },
      slots: { default: 'listOperationCondition' },
      title: '查询方式',
    },
    {
      align: 'center',
      field: 'nullable',
      slots: { default: 'nullable' },
      title: '允许空',
      width: 80,
    },
    {
      field: 'htmlType',
      minWidth: 140,
      params: { options: htmlTypeOptions },
      slots: { default: 'htmlType' },
      title: '显示类型',
    },
    {
      field: 'dictType',
      minWidth: 160,
      slots: { default: 'dictType' },
      title: '字典类型',
    },
    {
      field: 'example',
      minWidth: 140,
      slots: { default: 'example' },
      title: '示例',
    },
  ];
}
