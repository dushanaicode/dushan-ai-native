import type { UserInfo } from '@vben/types';
import type { Router, RouteRecordRaw } from 'vue-router';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createApp } from 'vue';
import { createPinia, setActivePinia } from 'pinia';
import { createMemoryHistory, createRouter } from 'vue-router';

import { useAccessStore, useTabbarStore, useUserStore } from '@vben/stores';
import { cloneDeep } from '@vben/utils';

import { createRouterGuard } from '../../dushan-admin-frontend/apps/web-ele/src/router/guard';
import { installSessionAccess } from '../../dushan-admin-frontend/apps/web-ele/src/router/session-access';
import {
  SessionCoordinator,
  SessionChangedError,
} from '../../dushan-admin-frontend/apps/web-ele/src/services/session/coordinator';
import { useAuthStore } from '../../dushan-admin-frontend/apps/web-ele/src/store/auth';

const stubs = vi.hoisted(() => ({
  login: vi.fn(),
  logout: vi.fn(),
  info: vi.fn(),
  notify: vi.fn(),
  generate: vi.fn(),
  session: undefined as unknown as SessionCoordinator,
}));
vi.mock('#/api', () => ({
  loginApi: stubs.login,
  logoutApi: stubs.logout,
  getPermissionInfoApi: stubs.info,
}));
vi.mock('#/locales', () => ({ $t: (key: string) => key }));
vi.mock('#/services/session/runtime', () => ({
  getSession: () => stubs.session,
}));
vi.mock('#/router/access', () => ({ generateAccess: stubs.generate }));
vi.mock('#/router/routes', () => ({
  accessRoutes: [],
  coreRouteNames: ['Root', 'Login', 'Home'],
}));
vi.mock('element-plus', () => ({ ElNotification: stubs.notify }));
vi.mock('@vben/preferences', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@vben/preferences')>();
  return {
    ...actual,
    preferences: {
      ...actual.preferences,
      app: {
        ...actual.preferences.app,
        loginExpiredMode: 'modal',
        defaultHomePath: '/home',
      },
      transition: { ...actual.preferences.transition, progress: false },
    },
  };
});

const Page = { render: () => null };
const user: UserInfo = {
  userId: '9223372036854775807',
  username: 'user',
  realName: '用户',
  avatar: '',
  roles: ['admin'],
  homePath: '/home',
  desc: '',
  token: '',
};
const cleanups: Array<() => void> = [];
/** 后端 /system/auth/get-permission-info 的一次响应：身份、权限码与授权菜单同源。 */
function permissionInfo(roles: string[] = ['admin']) {
  return { user: { ...user, roles }, permissions: ['read'], menus: [] };
}

beforeEach(() => {
  vi.resetAllMocks();
  stubs.login.mockResolvedValue({ accessToken: 'new-token' });
  stubs.logout.mockResolvedValue(undefined);
  stubs.info.mockResolvedValue(permissionInfo());
  stubs.generate.mockImplementation(
    async ({ router, roles }: { roles: string[]; router: Router }) => {
      const name = roles.includes('admin') ? 'admin' : 'member';
      const route = {
        name,
        path: `/${name}`,
        component: Page,
        meta: { title: name },
      };
      router.addRoute('Root', route);
      return { accessibleMenus: [], accessibleRoutes: [route] };
    },
  );
});
afterEach(() => {
  for (const cleanup of cleanups.splice(0)) cleanup();
});

async function fixture() {
  const pinia = createPinia();
  setActivePinia(pinia);
  const access = useAccessStore();
  const users = useUserStore();
  const tabs = useTabbarStore();
  const routes: RouteRecordRaw[] = [
    {
      name: 'Root',
      path: '/',
      component: Page,
      redirect: '/home',
      children: [{ name: 'Home', path: 'home', component: Page }],
    },
    { name: 'Login', path: '/auth/login', component: Page },
    { name: 'not-found', path: '/:path(.*)*', component: Page },
  ];
  const router = createRouter({
    history: createMemoryHistory(),
    routes: cloneDeep(routes),
  });
  const app = createApp(Page);
  app.use(pinia);
  app.use(router);
  app.mount(document.createElement('div'));
  await router.isReady();
  let shared = { generation: 'first', token: 'old-token' as null | string };
  access.setAccessToken(shared.token);
  const session = new SessionCoordinator({
    read: () => shared,
    write: (value) => {
      shared = { ...value };
      access.setAccessToken(value.token);
    },
    expire: async () => {},
    refresh: async () => 'refreshed',
    lock: (operation) => operation(),
    subscribe: () => () => {},
  });
  stubs.session = session;
  session.subscribe((next) => access.setAccessToken(next.token));
  const auth = app.runWithContext(() => useAuthStore());
  const external = vi.fn();
  const release = installSessionAccess({
    session,
    router,
    routes,
    clear: auth.clearSessionAccess,
    onExternalChange: external,
  });
  cleanups.push(() => {
    release();
    session.dispose();
    app.unmount();
  });
  return {
    access,
    auth,
    router,
    session,
    tabs,
    users,
    external,
    changeExternal: () => {
      shared = { generation: 'external', token: 'external-token' };
    },
  };
}

describe('实际认证 store 与路由边界', () => {
  it('会话清理卸载内容，新的权限导航完成后才允许重新挂载', async () => {
    const { router, session, tabs } = await fixture();
    createRouterGuard(router);
    await router.push('/admin');
    expect(tabs.renderRouteView).toBe(true);
    session.replace('other-user');
    expect(tabs.renderRouteView).toBe(false);
    const pending = Promise.withResolvers<ReturnType<typeof permissionInfo>>();
    stubs.info.mockReturnValue(pending.promise);
    const navigation = router.push('/member');
    await Promise.resolve();
    expect(tabs.renderRouteView).toBe(false);
    pending.resolve(permissionInfo(['member']));
    await navigation;
    expect(tabs.renderRouteView).toBe(true);
    expect(router.hasRoute('admin')).toBe(false);
  });

  it('登录跳转或成功回调期间切换身份，不再显示旧用户欢迎提示', async () => {
    const { auth, session } = await fixture();
    const pending = Promise.withResolvers<void>();
    const onSuccess = vi.fn(() => pending.promise);
    const result = Promise.allSettled([
      auth.authLogin({ username: 'u', password: 'p' }, onSuccess),
    ]);
    await vi.waitFor(() => expect(onSuccess).toHaveBeenCalledOnce());
    session.replace('another-user');
    pending.resolve();
    expect((await result)[0]).toMatchObject({
      status: 'rejected',
      reason: expect.any(SessionChangedError),
    });
    expect(stubs.notify).not.toHaveBeenCalled();
  });

  it('有令牌的退出只调用一次接口，失败仍撤销路由/缓存/用户；无令牌不再访问接口', async () => {
    const { access, auth, router, session, tabs, users } = await fixture();
    router.addRoute('Root', {
      name: 'secret',
      path: '/secret',
      component: Page,
    });
    users.setUserInfo(user);
    access.setAccessCodes(['admin']);
    access.setIsAccessChecked(true);
    tabs.cachedTabs.add('secret');
    tabs.cachedRoutes.set('secret', {} as never);
    const failure = new Error('退出接口失败');
    stubs.logout.mockRejectedValue(failure);
    const generation = session.capture().generation;
    const operation = auth.logout(false);
    const results = await Promise.allSettled([operation, auth.logout(false)]);
    expect(results).toEqual([
      { status: 'rejected', reason: failure },
      { status: 'rejected', reason: failure },
    ]);
    expect(stubs.logout).toHaveBeenCalledOnce();
    expect(session.capture().generation).not.toBe(generation);
    expect(access.accessToken).toBeNull();
    expect(access.accessCodes).toEqual([]);
    expect(access.isAccessChecked).toBe(false);
    expect(users.userInfo).toBeNull();
    expect(tabs.cachedTabs.size + tabs.cachedRoutes.size).toBe(0);
    expect(router.hasRoute('secret')).toBe(false);
    expect(router.currentRoute.value.path).toBe('/auth/login');
    await auth.logout(false);
    expect(stubs.logout).toHaveBeenCalledOnce();
  });

  it('过期重登录保持当前 URL，不执行普通成功回调或欢迎提示', async () => {
    const { access, auth, router, users } = await fixture();
    access.setLoginExpired(true);
    const onSuccess = vi.fn();
    const push = vi.spyOn(router, 'push');
    await auth.authLogin(
      { username: 'u', password: 'p', verification: 'verified' },
      onSuccess,
    );
    expect(access.loginExpired).toBe(false);
    expect(router.currentRoute.value.path).toBe('/home');
    expect(push).not.toHaveBeenCalled();
    expect(onSuccess).not.toHaveBeenCalled();
    expect(stubs.notify).not.toHaveBeenCalled();
    expect(users.userInfo?.userId).toBe('9223372036854775807');
    await auth.authLogin({ username: 'u', password: 'p' }, onSuccess);
    expect(onSuccess).toHaveBeenCalledOnce();
    expect(stubs.notify).toHaveBeenCalledOnce();
  });

  it('登录开始就撤销旧权限，建立令牌后用户资料失败不会留下半登录状态', async () => {
    const { access, auth, router } = await fixture();
    router.addRoute('Root', {
      name: 'secret',
      path: '/secret',
      component: Page,
    });
    const pending = Promise.withResolvers<{ accessToken: string }>();
    stubs.login.mockReturnValue(pending.promise);
    const failure = new Error('用户资料失败');
    stubs.info.mockRejectedValue(failure);
    const operation = auth.authLogin({ username: 'u', password: 'p' });
    const result = Promise.allSettled([operation]);
    expect(router.hasRoute('secret')).toBe(false);
    pending.resolve({ accessToken: 'new' });
    expect((await result)[0]).toEqual({ status: 'rejected', reason: failure });
    expect(access.accessToken).toBeNull();
    expect(auth.loginLoading).toBe(false);
    expect(stubs.logout).not.toHaveBeenCalled();
  });

  it('守卫在未收到事件但持久代次已经变化时重建权限，不沿用已检查标记', async () => {
    const { access, router, changeExternal, external } = await fixture();
    createRouterGuard(router);
    await router.push('/admin');
    expect(stubs.generate).toHaveBeenCalledOnce();
    expect(access.isAccessChecked).toBe(true);
    stubs.info.mockResolvedValue(permissionInfo(['member']));
    changeExternal();
    await router.push('/member');
    expect(stubs.generate).toHaveBeenCalledTimes(2);
    expect(external).toHaveBeenCalledOnce();
    expect(router.hasRoute('admin')).toBe(false);
    expect(router.resolve('/admin').name).toBe('not-found');
    expect(access.isAccessChecked).toBe(true);
  });
});
