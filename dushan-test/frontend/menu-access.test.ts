import type { RouteRecordRaw } from 'vue-router';

import { describe, expect, it, vi } from 'vitest';
import { createMemoryHistory, createRouter } from 'vue-router';

import { cloneDeep } from '@vben/utils';

import {
  menusToRoutes,
  parseMenus,
  type MenuNode,
} from '../../dushan-admin-frontend/apps/web-ele/src/router/menu-adapter';
import {
  installSessionAccess,
  readRedirect,
  reportNavigationFailure,
  restoreBaseRoutes,
  scopedRouter,
} from '../../dushan-admin-frontend/apps/web-ele/src/router/session-access';
import {
  SessionChangedError,
  SessionCoordinator,
} from '../../dushan-admin-frontend/apps/web-ele/src/services/session/coordinator';
import { generateAccessible } from '../../dushan-admin-frontend/packages/effects/access/src/accessible';

const Page = { render: () => null };
it('导航与外部同步错误不记录请求凭据，调用方仍收到原错误', async () => {
  const output = vi.spyOn(console, 'error').mockImplementation(() => undefined);
  const error = Object.assign(new Error('private-message'), {
    config: { headers: { Authorization: 'Bearer private-token' } },
  });
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: Page }],
  });
  router.onError(reportNavigationFailure);
  router.beforeEach(() => {
    throw error;
  });
  try {
    await expect(router.push('/')).rejects.toBe(error);
    await Promise.reject(error).catch(reportNavigationFailure);
    expect(output.mock.calls).toEqual([
      ['页面导航失败，请检查界面中的请求提示'],
      ['页面导航失败，请检查界面中的请求提示'],
    ]);
    expect(JSON.stringify(output.mock.calls)).not.toContain('private-');
  } finally {
    output.mockRestore();
    router.options.history.destroy();
  }
});
const pageMap = { '../views/page.vue': async () => ({ default: Page }) };
const layouts = {
  IFrameView: async () => Page,
  RouterView: async () => Page,
  ExternalLinkView: async () => Page,
};
const reserved = new Set(['/', '/auth/login']);
const base: RouteRecordRaw[] = [
  { name: 'Root', path: '/', component: Page, children: [] },
];
const menu = (values: Partial<MenuNode>): MenuNode => ({
  id: '1',
  title: '页面',
  path: '/page',
  kind: 'page',
  order: 0,
  component: '/page.vue',
  children: [],
  ...values,
});

function sessionFixture() {
  let snapshot = { generation: 'initial', token: 'first' as null | string };
  const session = new SessionCoordinator({
    read: () => snapshot,
    write: (value) => {
      snapshot = { ...value };
    },
    lock: (operation) => operation(),
    refresh: async () => 'next',
    expire: async () => {},
    subscribe: () => () => {},
  });
  return {
    session,
    external: () => {
      snapshot = { generation: 'external', token: 'external' };
      session.capture();
    },
  };
}

describe('菜单纯函数与协议边界', () => {
  it('字符串 ID、排序与显示属性保留，输入不变，重复转换一致且名称不依赖标题', () => {
    const input = [
      menu({ id: '9223372036854775807', order: 1 }),
      menu({
        id: '2',
        path: '/first',
        order: 0,
        hidden: false,
        keepAlive: true,
        forbidden: true,
      }),
    ];
    const before = JSON.stringify(input);
    const first = menusToRoutes(input, pageMap, layouts, reserved);
    expect(first).toEqual(menusToRoutes(input, pageMap, layouts, reserved));
    expect(JSON.stringify(input)).toBe(before);
    expect(first.map((route) => route.name)).toEqual([
      'menu-2',
      'menu-9223372036854775807',
    ]);
    expect(first[0]?.meta).toMatchObject({
      order: 0,
      hideInMenu: false,
      keepAlive: true,
      menuVisibleWithForbidden: true,
    });
    input[0]!.title = '改名';
    expect(menusToRoutes(input, pageMap, layouts, reserved)[1]?.name).toBe(
      first[1]?.name,
    );
    expect(() =>
      parseMenus([{ ...input[0], id: 9_223_372_036_854_775_807 }]),
    ).toThrow();
  });

  it('嵌套重定向使用完整路径，参数子路由不生成字面量重定向', () => {
    const input = [
      menu({
        id: 'root',
        kind: 'group',
        path: '/system',
        children: [
          menu({
            id: 'users',
            kind: 'group',
            path: 'users',
            children: [menu({ id: 'list', path: 'list' })],
          }),
        ],
      }),
    ];
    const routes = menusToRoutes(input, pageMap, layouts, reserved);
    expect(routes[0]?.redirect).toBe('/system/users');
    expect(routes[0]?.children?.[0]?.redirect).toBe('/system/users/list');
    const parameters = menusToRoutes(
      [
        menu({
          id: 'parent',
          path: '/people',
          children: [menu({ id: 'child', path: 'details/:id' })],
        }),
      ],
      pageMap,
      layouts,
      reserved,
    );
    expect(parameters[0]?.redirect).toBeUndefined();
    expect(parameters[0]?.children?.[0]?.path).toBe('/people/details/:id');
  });

  it('外链与 iframe 显式区分，动作不生成路由，非法组件/URL/重复/保留路径拒绝', () => {
    const routes = menusToRoutes(
      [
        menu({
          id: 'link',
          kind: 'link',
          path: '/docs',
          url: 'https://example.com/docs',
        }),
        menu({
          id: 'frame',
          kind: 'iframe',
          path: '/frame',
          url: 'https://example.com/frame',
        }),
        menu({ id: 'button', kind: 'action', path: '' }),
      ],
      pageMap,
      layouts,
      reserved,
    );
    expect(routes).toHaveLength(2);
    expect(routes[0]?.meta.link).toBe('https://example.com/docs');
    expect(routes[1]?.meta.iframeSrc).toBe('https://example.com/frame');
    expect(routes[1]?.component).toBe('IFrameView');
    for (const invalid of [
      [menu({ component: '/missing.vue' })],
      [menu({ kind: 'iframe', url: 'javascript:alert(1)' })],
      [menu({ kind: 'link', url: 'https://user:password@example.com' })],
      [menu({ path: '/auth/login' })],
      [menu({}), menu({})],
      [menu({}), menu({ id: 'different' })],
    ])
      expect(() =>
        menusToRoutes(invalid, pageMap, layouts, reserved),
      ).toThrow();
  });

  it('外部跳转参数只允许应用内路径，拒绝数组、外站和无效编码', () => {
    expect(readRedirect(encodeURIComponent('/users?q=1'), '/')).toBe(
      '/users?q=1',
    );
    for (const input of [
      '//example.com',
      'https://example.com',
      '%zz',
      ['/users'],
    ])
      expect(() => readRedirect(input, '/')).toThrow();
  });
});

describe('真实 Router 的权限撤销与异步生成', () => {
  it('mixed 保留前端工具路由，后端同名配置优先，并保留权限过滤与 403 展示', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: cloneDeep(base),
    });
    const Forbidden = { render: () => null };
    const result = await generateAccessible('mixed', {
      router,
      roles: ['member'],
      pageMap,
      layoutMap: layouts,
      forbiddenComponent: Forbidden,
      routes: [
        {
          name: 'menu-1',
          path: '/front',
          component: Page,
          meta: { title: 'front', authority: ['member'] },
        },
        {
          name: 'tool',
          path: '/tool',
          component: Page,
          meta: { title: 'tool', authority: ['member'] },
        },
        {
          name: 'admin-only',
          path: '/admin',
          component: Page,
          meta: { title: 'admin', authority: ['admin'] },
        },
      ],
      fetchMenuListAsync: async () =>
        menusToRoutes(
          [menu({ path: '/backend', forbidden: true })],
          pageMap,
          layouts,
          reserved,
        ),
    });
    expect(router.hasRoute('tool')).toBe(true);
    expect(router.hasRoute('admin-only')).toBe(false);
    const backend = result.accessibleRoutes.find(
      (route) => route.name === 'menu-1',
    );
    expect(backend?.path).toBe('/backend');
    expect(backend?.component).toBe(Forbidden);
  });

  it('撤销后再生成不会让旧 root.children 中的路由复活，基础路由输入保持干净', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: cloneDeep(base),
    });
    await generateAccessible('frontend', {
      router,
      roles: [],
      routes: [
        { name: 'old', path: '/old', component: Page, meta: { title: 'old' } },
      ],
    });
    expect(router.hasRoute('old')).toBe(true);
    expect(base[0]?.children).toEqual([]);
    restoreBaseRoutes(router, base);
    await generateAccessible('frontend', {
      router,
      roles: [],
      routes: [
        { name: 'new', path: '/new', component: Page, meta: { title: 'new' } },
      ],
    });
    expect(router.hasRoute('old')).toBe(false);
    expect(router.hasRoute('new')).toBe(true);
    expect(
      router
        .getRoutes()
        .find((route) => route.name === 'Root')
        ?.children.map((route) => route.name),
    ).toEqual(['new']);
  });

  it('代次边界撤销路由并清缓存，只有外部身份变化触发额外导航', () => {
    const { session, external } = sessionFixture();
    const router = createRouter({
      history: createMemoryHistory(),
      routes: cloneDeep(base),
    });
    router.addRoute('Root', {
      name: 'restricted',
      path: '/restricted',
      component: Page,
    });
    const clear = vi.fn();
    const onExternalChange = vi.fn();
    const release = installSessionAccess({
      session,
      router,
      routes: base,
      clear,
      onExternalChange,
    });
    session.replace('other');
    expect(router.hasRoute('restricted')).toBe(false);
    expect(clear).toHaveBeenCalledOnce();
    expect(onExternalChange).not.toHaveBeenCalled();
    external();
    expect(onExternalChange).toHaveBeenCalledOnce();
    release();
    session.dispose();
  });

  it('在后端菜单挂起时切换代次，旧生成任务不能重新添加路由', async () => {
    const { session } = sessionFixture();
    const router = createRouter({
      history: createMemoryHistory(),
      routes: cloneDeep(base),
    });
    const scope = session.capture();
    const pending = Promise.withResolvers<ReturnType<typeof menusToRoutes>>();
    const loading = generateAccessible('backend', {
      router: scopedRouter(router, () => session.assertCurrent(scope)),
      routes: [],
      roles: [],
      pageMap,
      layoutMap: layouts,
      fetchMenuListAsync: () => pending.promise,
    });
    const result = Promise.allSettled([loading]);
    session.replace('new-user');
    pending.resolve(menusToRoutes([menu({})], pageMap, layouts, reserved));
    expect((await result)[0]).toMatchObject({
      status: 'rejected',
      reason: expect.any(SessionChangedError),
    });
    expect(router.hasRoute('menu-1')).toBe(false);
  });
});
