import { createApp, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';

import { initStores, useUserStore } from '@vben/stores';

import { afterEach, assert, expect, it, vi } from 'vitest';

import ReadonlyDemoBadge from '../../dushan-admin-frontend/apps/web-ele/src/components/readonly-demo-badge.vue';
import { setupSession } from '../../dushan-admin-frontend/apps/web-ele/src/services/session/runtime';
import { useAuthStore } from '../../dushan-admin-frontend/apps/web-ele/src/store/auth';

const stubs = vi.hoisted(() => ({
  info: vi.fn(),
  login: vi.fn(),
  notification: vi.fn(),
}));
vi.mock('#/api', () => ({
  getPermissionInfoApi: stubs.info,
  loginApi: stubs.login,
  logoutApi: vi.fn(),
  smsLoginApi: vi.fn(),
  registerApi: vi.fn(),
  socialLoginApi: vi.fn(),
}));
vi.mock('#/locales', async () => {
  const { default: messages } =
    await import('../../dushan-admin-frontend/apps/web-ele/src/locales/langs/zh-CN/readonlyDemo.json');
  return {
    $t: (key: string) =>
      key.startsWith('readonlyDemo.')
        ? messages[key.split('.')[1] as keyof typeof messages]
        : key,
  };
});
vi.mock('element-plus', async (importOriginal) => ({
  ...(await importOriginal<typeof import('element-plus')>()),
  ElNotification: stubs.notification,
}));
const cleanups: Array<() => void> = [];
afterEach(() => {
  for (const cleanup of cleanups.splice(0)) cleanup();
  localStorage.clear();
  vi.clearAllMocks();
});
async function fixture(roles: string[]) {
  const host = document.createElement('div');
  document.body.append(host);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { render: () => null } },
      { path: '/home', component: { render: () => null } },
    ],
  });
  const app = createApp(() => h(ReadonlyDemoBadge));
  await initStores(app, { namespace: 'readonly-demo-test' });
  app.use(router);
  await router.push('/');
  await router.isReady();
  const session = setupSession({
    namespace: 'readonly-demo-test',
    expire: async () => {},
    refresh: async () => 'refreshed',
  });
  const auth = app.runWithContext(() => useAuthStore());
  const user = useUserStore();
  app.mount(host);
  cleanups.push(() => {
    app.unmount();
    session.dispose();
    host.remove();
  });
  stubs.login.mockResolvedValue({ accessToken: 'demo-token', tenantId: '1' });
  stubs.info.mockResolvedValue({
    tenantId: '1',
    menus: [],
    permissions: [],
    user: {
      userId: '101',
      username: 'demo',
      realName: '演示',
      roles,
      homePath: '/home',
      avatar: '',
      desc: '',
      token: '',
    },
  });
  return { auth, user, host };
}
it('只读角色显示标识和悬停说明，角色切换及退出后隐藏', async () => {
  const { auth, user, host } = await fixture(['readonly']);
  expect(host.textContent).toBe('');
  await auth.authLogin({ username: 'demo', password: 'password' });
  await nextTick();
  expect(host.textContent).toBe('只读演示');
  const badge = host.querySelector('[tabindex="0"]');
  assert(badge);
  badge.dispatchEvent(new FocusEvent('focus'));
  await vi.waitFor(() =>
    expect(document.body.textContent).toContain(
      '当前为只读演示账号：可以浏览演示开放的功能，修改操作不会生效',
    ),
  );
  user.setUserRoles(['super_admin']);
  await nextTick();
  expect(host.textContent).toBe('');
  user.$reset();
  await nextTick();
  expect(host.textContent).toBe('');
});
it('同一次成功登录只提示一次，权限刷新不重复；普通账号维持成功通知', async () => {
  const { auth } = await fixture(['readonly']);
  const login = auth.authLogin({ username: 'demo', password: 'password' });
  await Promise.all([
    login,
    auth.authLogin({ username: 'demo', password: 'password' }),
  ]);
  expect(stubs.login).toHaveBeenCalledOnce();
  await auth.fetchUserInfo();
  expect(stubs.notification).toHaveBeenCalledExactlyOnceWith({
    message: '已进入只读演示模式',
    type: 'warning',
  });
  const info = await stubs.info();
  stubs.info.mockResolvedValue({
    ...info,
    user: { ...info.user, roles: ['super_admin'] },
  });
  stubs.notification.mockClear();
  await auth.authLogin({ username: 'admin', password: 'password' });
  expect(stubs.notification).toHaveBeenCalledExactlyOnceWith(
    expect.objectContaining({ type: 'success' }),
  );
});
