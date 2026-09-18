import type {
  ComponentRecordType,
  RouteRecordStringComponent,
} from '@vben/types';

import { z } from '@vben/common-ui';

export interface MenuNode {
  children: MenuNode[];
  component?: string;
  forbidden?: boolean;
  hidden?: boolean;
  icon?: string;
  id: string;
  keepAlive?: boolean;
  kind: 'action' | 'group' | 'iframe' | 'link' | 'page';
  order: number;
  path: string;
  title: string;
  url?: string;
}

const menuSchema: z.ZodType<MenuNode> = z.lazy(() =>
  z
    .object({
      children: z.array(menuSchema),
      component: z.string().min(1).optional(),
      forbidden: z.boolean().optional(),
      hidden: z.boolean().optional(),
      icon: z.string().optional(),
      id: z.string().min(1),
      keepAlive: z.boolean().optional(),
      kind: z.enum(['action', 'group', 'iframe', 'link', 'page']),
      order: z.number().finite(),
      path: z.string(),
      title: z.string().min(1),
      url: z.string().optional(),
    })
    .strict(),
);

export function parseMenus(value: unknown): MenuNode[] {
  return z.array(menuSchema).parse(value);
}

/** 菜单配置可以指向本次构建未包含的页面，用上游的"即将上线"页承接。 */
const COMING_SOON_PAGE = '/_core/fallback/coming-soon.vue';

export function menusToRoutes(
  menus: MenuNode[],
  pageMap: ComponentRecordType,
  layoutMap: ComponentRecordType,
  reservedPaths: ReadonlySet<string>,
): RouteRecordStringComponent[] {
  const pages = new Set(
    Object.keys(pageMap).map((key) => `/${key.replace(/^\.\.\/views\//, '')}`),
  );
  if (!pages.has(COMING_SOON_PAGE))
    throw new TypeError(`兜底页面未登记：${COMING_SOON_PAGE}`);
  const ids = new Set<string>();
  const paths = new Set(reservedPaths);
  function convert(
    nodes: MenuNode[],
    parentPath: string,
  ): RouteRecordStringComponent[] {
    return nodes
      .toSorted((left, right) => left.order - right.order)
      .flatMap((node) => {
        if (ids.has(node.id)) throw new TypeError(`菜单 ID 重复：${node.id}`);
        ids.add(node.id);
        if (
          ['action', 'iframe', 'link'].includes(node.kind) &&
          node.children.length > 0
        )
          throw new TypeError(`叶子菜单不能包含子菜单：${node.id}`);
        if (node.kind === 'action') return [];
        if (
          !node.path ||
          node.path.includes('?') ||
          node.path.includes('#') ||
          node.path.includes('\\') ||
          node.path.startsWith('//')
        )
          throw new TypeError(`菜单路径无效：${node.id}`);
        const path = node.path.startsWith('/')
          ? node.path
          : `${parentPath}/${node.path}`;
        if (paths.has(path))
          throw new TypeError(`菜单路径重复或被保留：${path}`);
        paths.add(path);
        const meta: NonNullable<RouteRecordStringComponent['meta']> = {
          title: node.title,
          order: node.order,
          hideInMenu: node.hidden,
          keepAlive: node.keepAlive,
          menuVisibleWithForbidden: node.forbidden,
          icon: node.icon,
        };
        const route: RouteRecordStringComponent = {
          name: `menu-${node.id}`,
          path,
          component: 'RouterView',
          meta,
        };
        if (node.kind === 'group' && !layoutMap.RouterView)
          throw new TypeError('RouterView 尚未登记');
        if (node.kind === 'page') {
          // 菜单存在数据库、超管拿到全部菜单，构建里缺页面不能让整棵树失败导致无法登录。
          route.component =
            node.component && pages.has(node.component)
              ? node.component
              : COMING_SOON_PAGE;
        }
        if (node.kind === 'link' || node.kind === 'iframe') {
          if (!node.url) throw new TypeError(`菜单 URL 缺失：${node.id}`);
          const url = new URL(node.url);
          if (
            !['http:', 'https:'].includes(url.protocol) ||
            url.username ||
            url.password
          )
            throw new TypeError(`菜单 URL 不允许：${node.id}`);
          if (node.kind === 'link') {
            if (!layoutMap.ExternalLinkView)
              throw new TypeError('ExternalLinkView 尚未登记');
            route.component = 'ExternalLinkView';
            meta.link = url.href;
          } else {
            if (!layoutMap.IFrameView)
              throw new TypeError('IFrameView 尚未登记');
            route.component = 'IFrameView';
            meta.iframeSrc = url.href;
          }
        }
        route.children = convert(node.children, path);
        const first = route.children[0];
        // 输出绝对路径，避免引擎再次拼接深层路径或跳到未填充的参数。
        if (first && !first.path.includes(':') && !first.meta?.link)
          route.redirect = first.path;
        return [route];
      });
  }
  return convert(menus, '');
}
