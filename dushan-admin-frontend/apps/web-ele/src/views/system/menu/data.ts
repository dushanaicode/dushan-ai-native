import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { SystemMenuApi } from '#/api/system/menu';
import type { SwitchStatusValue } from '#/constants/status';

import { isHttpUrl } from '@vben/utils';

import { z } from '#/adapter/form';
import { getMenuList } from '#/api/system/menu';
import { DICT_TYPE } from '#/constants/dict-types';
import { SwitchStatus } from '#/constants/status';
import { useDictionary } from '#/services/dictionary/context';

interface MenuTreeNode extends SystemMenuApi.MenuRespVO {
  children?: MenuTreeNode[];
  disabled?: boolean;
}

const booleanOptions = [
  { label: '是', value: true },
  { label: '否', value: false },
];

const visibleOptions = [
  { label: '显示', value: true },
  { label: '隐藏', value: false },
];

/** 菜单类型选项：与后端 MenuVO.kind 一致（非 system_menu_type 字典）。 */
export const menuKindOptions = [
  { label: '目录', value: 'group' },
  { label: '菜单', value: 'page' },
  { label: '按钮', value: 'action' },
  { label: '链接', value: 'link' },
  { label: '内嵌', value: 'iframe' },
] as const;

const menuKindLabels: Record<SystemMenuApi.MenuKind, string> = {
  action: '按钮',
  group: '目录',
  iframe: '内嵌',
  link: '链接',
  page: '菜单',
};

export function menuKindLabel(kind: SystemMenuApi.MenuKind) {
  return menuKindLabels[kind] ?? kind;
}

const viewModules = import.meta.glob([
  '../../**/*.vue',
  '!../../**/modules/**/*.vue',
]);
const routeComponentOptions = Object.keys(viewModules)
  .map((path) => {
    const value = path.replace(/^..\/..\//, '').replace(/\.vue$/, '');
    return { label: value, value };
  })
  .toSorted((a, b) => a.value.localeCompare(b.value));

function buildMenuTree(
  list: SystemMenuApi.MenuRespVO[],
  excludeId?: string,
): MenuTreeNode[] {
  const nodeMap = new Map<string, MenuTreeNode>();
  const roots: MenuTreeNode[] = [];

  for (const item of list) {
    if (item.id === excludeId) continue;
    nodeMap.set(item.id, {
      ...item,
      // 按钮/链接/内嵌不能作为父级
      disabled: item.kind !== 'group' && item.kind !== 'page',
    });
  }

  for (const item of list) {
    if (item.id === excludeId) continue;

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

function isDirOrMenu(kind?: string) {
  return kind === 'group' || kind === 'page';
}

function isMenu(kind?: string) {
  return kind === 'page';
}

function isButton(kind?: string) {
  return kind === 'action';
}

function isExternal(kind?: string) {
  return kind === 'link' || kind === 'iframe';
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
      component: 'ApiTreeSelect',
      componentProps: (ctx) => {
        return {
          api: async () => {
            const data = await getMenuList();
            return [
              {
                children: buildMenuTree(data, ctx.rootValues?.id),
                id: '0',
                kind: 'group',
                name: '顶级菜单',
                parentId: '-1',
              },
            ];
          },
          checkStrictly: true,
          childrenField: 'children',
          clearable: true,
          labelField: 'name',
          nodeKey: 'id',
          placeholder: '请选择上级菜单',
          props: { children: 'children', disabled: 'disabled', label: 'name' },
          treeDefaultExpandAll: true,
          valueField: 'id',
        };
      },
      dependencies: {
        triggerFields: ['id'],
      },
      fieldName: 'parentId',
      label: '上级菜单',
      rules: 'selectRequired',
    },
    {
      component: 'Input',
      componentProps: {
        maxlength: 50,
        placeholder: '请输入菜单名称',
        showWordLimit: true,
      },
      fieldName: 'name',
      label: '菜单名称',
      rules: 'required',
    },
    {
      component: 'RadioGroup',
      componentProps: {
        isButton: true,
        options: menuKindOptions,
      },
      fieldName: 'kind',
      label: '菜单类型',
      rules: z.string().default('group'),
    },
    {
      component: 'IconPicker',
      componentProps: {
        clearable: true,
        placeholder: '请选择菜单图标',
      },
      dependencies: {
        rules: (values) =>
          isDirOrMenu(values.kind)
            ? requiredString('请选择菜单图标')
            : z.string().optional(),
        show: (values) => isDirOrMenu(values.kind),
        triggerFields: ['kind'],
      },
      fieldName: 'icon',
      label: '菜单图标',
    },
    {
      component: 'Input',
      componentProps: {
        maxlength: 200,
        placeholder: '请输入路由地址',
        showWordLimit: true,
      },
      dependencies: {
        rules: (values) => {
          if (!isDirOrMenu(values.kind)) return z.string().optional();

          return requiredString('请输入路由地址').refine((value) => {
            if (isHttpUrl(value)) return true;
            return values.parentId === '0'
              ? value.startsWith('/')
              : !value.startsWith('/');
          }, '顶级菜单路由地址必须以 / 开头，子级菜单路由地址不能以 / 开头');
        },
        show: (values) => isDirOrMenu(values.kind),
        triggerFields: ['kind', 'parentId'],
      },
      fieldName: 'path',
      label: '路由地址',
    },
    {
      component: 'Input',
      componentProps: {
        maxlength: 200,
        placeholder: '请输入外部地址（http/https）',
        showWordLimit: true,
      },
      dependencies: {
        rules: (values) =>
          isExternal(values.kind)
            ? requiredString('请输入外部地址').refine(
                (value) => isHttpUrl(value),
                '外部地址必须是合法的 http/https 地址',
              )
            : z.string().optional(),
        show: (values) => isExternal(values.kind),
        triggerFields: ['kind'],
      },
      fieldName: 'url',
      label: '外部地址',
    },
    {
      component: 'Select',
      componentProps: {
        allowCreate: true,
        clearable: true,
        filterable: true,
        options: routeComponentOptions,
        placeholder: '请选择或输入组件路径',
      },
      dependencies: {
        rules: (values) =>
          isMenu(values.kind)
            ? requiredString('请选择或输入组件路径')
            : z.string().optional(),
        show: (values) => isMenu(values.kind),
        triggerFields: ['kind'],
      },
      fieldName: 'component',
      label: '组件路径',
    },
    {
      component: 'Input',
      componentProps: {
        maxlength: 100,
        placeholder: '请输入组件名称',
        showWordLimit: true,
      },
      dependencies: {
        rules: (values) =>
          isMenu(values.kind) && values.keepAlive
            ? requiredString('请输入组件名称')
            : z.string().optional(),
        show: (values) => isMenu(values.kind),
        triggerFields: ['kind', 'keepAlive'],
      },
      fieldName: 'componentName',
      label: '组件名称',
    },
    {
      component: 'Input',
      componentProps: {
        maxlength: 100,
        placeholder: '请输入权限标识',
        showWordLimit: true,
      },
      dependencies: {
        rules: (values) =>
          isButton(values.kind)
            ? requiredString('请输入权限标识')
            : z.string().optional(),
        show: (values) => isMenu(values.kind) || isButton(values.kind),
        triggerFields: ['kind'],
      },
      fieldName: 'permission',
      label: '权限标识',
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: 0,
        placeholder: '请输入显示顺序',
      },
      fieldName: 'sort',
      label: '显示顺序',
      rules: 'required',
    },
    {
      component: 'RadioGroup',
      componentProps: () => ({
        isButton: true,
        options: dictionary.getDictOptions(DICT_TYPE.COMMON_STATUS, 'number'),
      }),
      fieldName: 'status',
      label: '状态',
      rules: z.number().default(SwitchStatus.ENABLED),
    },
    {
      component: 'RadioGroup',
      componentProps: {
        isButton: true,
        options: visibleOptions,
      },
      dependencies: {
        show: (values) => isDirOrMenu(values.kind),
        triggerFields: ['kind'],
      },
      fieldName: 'visible',
      label: '显示状态',
      rules: z.boolean().default(true),
    },
    {
      component: 'RadioGroup',
      componentProps: {
        isButton: true,
        options: booleanOptions,
      },
      dependencies: {
        show: (values) => isMenu(values.kind),
        triggerFields: ['kind'],
      },
      fieldName: 'alwaysShow',
      label: '总是显示',
      rules: z.boolean().default(true),
    },
    {
      component: 'RadioGroup',
      componentProps: {
        isButton: true,
        options: [
          { label: '缓存', value: true },
          { label: '不缓存', value: false },
        ],
      },
      dependencies: {
        show: (values) => isMenu(values.kind),
        triggerFields: ['kind'],
      },
      fieldName: 'keepAlive',
      label: '缓存状态',
      rules: z.boolean().default(true),
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
        placeholder: '请输入菜单名称',
      },
      fieldName: 'name',
      label: '菜单名称',
    },
    {
      component: 'Select',
      componentProps: () => ({
        clearable: true,
        options: dictionary.getDictOptions(DICT_TYPE.COMMON_STATUS, 'number'),
        placeholder: '请选择状态',
      }),
      fieldName: 'status',
      label: '状态',
    },
  ];
}

export function useGridColumns(
  onStatusChange?: (
    newStatus: SwitchStatusValue,
    row: SystemMenuApi.MenuRespVO,
  ) => Promise<boolean | undefined>,
): VxeTableGridOptions<SystemMenuApi.MenuRespVO>['columns'] {
  return [
    { fixed: 'left', type: 'checkbox', width: 40 },
    {
      align: 'left',
      field: 'name',
      fixed: 'left',
      minWidth: 240,
      slots: { default: 'name' },
      title: '菜单名称',
      treeNode: true,
    },
    {
      field: 'kind',
      formatter: ({ cellValue }) => menuKindLabel(cellValue),
      minWidth: 100,
      title: '菜单类型',
    },
    {
      field: 'sort',
      minWidth: 100,
      title: '显示顺序',
    },
    {
      field: 'permission',
      minWidth: 180,
      title: '权限标识',
    },
    {
      field: 'path',
      minWidth: 180,
      title: '路由地址',
    },
    {
      field: 'component',
      minWidth: 220,
      title: '组件路径',
    },
    {
      field: 'componentName',
      minWidth: 160,
      title: '组件名称',
    },
    {
      align: 'center',
      cellRender: {
        name: 'CellSwitch',
        props: { change: onStatusChange },
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
      minWidth: 220,
      slots: { default: 'actions' },
      title: '操作',
    },
  ];
}
