import type { MenuNode } from './menu-adapter';

import { z } from '@vben/common-ui';

import { parseMenus } from './menu-adapter';

/**
 * 后端 `/system/auth/get-permission-info` 返回的菜单节点。
 *
 * 字段以 `module_system` 的 `MenuVO` 为准：标题为 `name`、显隐为 `visible`（与前端 `hidden`
 * 相反）、叶子节点 `children` 为 `null`。未在此声明的字段（`parentId`、`componentName`、
 * `alwaysShow`、`dataPermission`）由 zod 直接丢弃，不进入前端菜单契约。
 *
 * 后端该响应不含 `sort`，菜单顺序由服务端建树时给定，前端按同级下标承接。
 */
interface BackendMenu {
  children?: BackendMenu[] | null;
  component?: null | string;
  icon?: null | string;
  id: string;
  keepAlive: boolean;
  kind: 'action' | 'group' | 'iframe' | 'link' | 'page';
  name: string;
  path?: null | string;
  url?: null | string;
  visible: boolean;
}

const backendMenuSchema: z.ZodType<BackendMenu> = z.lazy(() =>
  z.object({
    children: z.array(backendMenuSchema).nullable().optional(),
    component: z.string().nullable().optional(),
    icon: z.string().nullable().optional(),
    id: z.string().min(1),
    keepAlive: z.boolean(),
    kind: z.enum(['action', 'group', 'iframe', 'link', 'page']),
    name: z.string().min(1),
    path: z.string().nullable().optional(),
    url: z.string().nullable().optional(),
    visible: z.boolean(),
  }),
);

/**
 * 后端 `component` 是 `views` 下不带扩展名的相对路径，例如 `system/user/index`；
 * 前端菜单契约与 `import.meta.glob` 登记键一致，为 `/system/user/index.vue`。
 */
function toPageKey(component: string) {
  const path = component.startsWith('/') ? component : `/${component}`;
  return path.endsWith('.vue') ? path : `${path}.vue`;
}

function toMenuNode(menu: BackendMenu, order: number): MenuNode {
  const component = menu.component ?? '';
  return {
    children: (menu.children ?? []).map((child, index) =>
      toMenuNode(child, index),
    ),
    component:
      menu.kind === 'page' && component ? toPageKey(component) : undefined,
    hidden: !menu.visible,
    icon: menu.icon || undefined,
    id: menu.id,
    keepAlive: menu.keepAlive,
    kind: menu.kind,
    order,
    path: menu.path ?? '',
    title: menu.name,
    url: menu.url ?? undefined,
  };
}

/** 校验后端菜单树并投影为前端菜单契约，投影结果再经 parseMenus 严格校验。 */
export function parseBackendMenus(value: unknown): MenuNode[] {
  const menus = z.array(backendMenuSchema).parse(value);
  return parseMenus(menus.map((menu, index) => toMenuNode(menu, index)));
}
