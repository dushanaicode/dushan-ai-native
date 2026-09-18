import { describe, expect, it } from 'vitest';

import { parseBackendMenus } from '../../dushan-admin-frontend/apps/web-ele/src/router/backend-menu';
import { overridesPreferences } from '../../dushan-admin-frontend/apps/web-ele/src/preferences';

/** 一个后端 MenuVO 节点，字段名与 module_system 的实际输出一致。 */
function backendMenu(values: Record<string, unknown> = {}) {
  return {
    alwaysShow: true,
    children: null,
    component: '',
    componentName: '',
    dataPermission: false,
    icon: '',
    id: '10000000000001',
    keepAlive: true,
    kind: 'group',
    name: '系统管理',
    parentId: '0',
    path: '/system',
    url: null,
    visible: true,
    ...values,
  };
}

describe('后端权限信息契约投影', () => {
  it('按后端真实字段投影菜单：name→title、visible→hidden、component 补登记键、null children 转空数组', () => {
    const [group] = parseBackendMenus([
      backendMenu({
        children: [
          backendMenu({
            component: 'system/user/index',
            componentName: 'SystemUser',
            icon: 'ep:user',
            id: '10000000000101',
            keepAlive: false,
            kind: 'page',
            name: '用户管理',
            parentId: '10000000000001',
            path: 'user',
            visible: false,
          }),
        ],
      }),
    ]);
    expect(group).toEqual({
      children: [
        {
          children: [],
          component: '/system/user/index.vue',
          hidden: true,
          icon: 'ep:user',
          id: '10000000000101',
          keepAlive: false,
          kind: 'page',
          order: 0,
          path: 'user',
          title: '用户管理',
          url: undefined,
        },
      ],
      component: undefined,
      hidden: false,
      icon: undefined,
      id: '10000000000001',
      keepAlive: true,
      kind: 'group',
      order: 0,
      path: '/system',
      title: '系统管理',
      url: undefined,
    });
  });

  it('order 取同级下标，保持后端建树给定的顺序', () => {
    const menus = parseBackendMenus([
      backendMenu({ id: '1', name: '第一', path: '/first' }),
      backendMenu({ id: '2', name: '第二', path: '/second' }),
      backendMenu({ id: '3', name: '第三', path: '/third' }),
    ]);
    expect(menus.map((menu) => [menu.title, menu.order])).toEqual([
      ['第一', 0],
      ['第二', 1],
      ['第三', 2],
    ]);
  });

  it('丢弃后端多余字段，不让严格校验因 parentId 等键整树失败', () => {
    const [node] = parseBackendMenus([backendMenu()]);
    for (const key of [
      'parentId',
      'componentName',
      'alwaysShow',
      'dataPermission',
      'name',
      'visible',
    ])
      expect(Object.hasOwn(node as object, key)).toBe(false);
  });

  it('外链与内嵌页保留 url，非法协议仍然拒绝', () => {
    const [link] = parseBackendMenus([
      backendMenu({
        kind: 'link',
        path: '/docs',
        url: 'https://example.com/docs',
      }),
    ]);
    expect(link?.url).toBe('https://example.com/docs');
    expect(() =>
      parseBackendMenus([
        backendMenu({ kind: 'link', path: '/docs', url: 42 }),
      ]),
    ).toThrow(expect.objectContaining({ name: 'ZodError' }));
  });

  it('后端菜单缺少必填字段时报告协议错误，不产生半个菜单树', () => {
    for (const invalid of [
      [backendMenu({ id: '' })],
      [backendMenu({ name: '' })],
      [backendMenu({ visible: null })],
      [backendMenu({ keepAlive: undefined })],
      [backendMenu({ kind: 'unknown' })],
      [{ id: '1', name: '缺字段' }],
    ])
      expect(() => parseBackendMenus(invalid)).toThrow(
        expect.objectContaining({ name: 'ZodError' }),
      );
  });
});

describe('应用权限模式配置', () => {
  it('web-ele 使用 mixed，动态菜单链路在运行时真的会执行', () => {
    // frontend 模式下 generateAccessible 不会调用 fetchMenuListAsync，
    // 纯 backend 模式会丢掉本地 dashboard 路由使 defaultHomePath 落到 404。
    expect(overridesPreferences.app?.accessMode).toBe('mixed');
  });
});
