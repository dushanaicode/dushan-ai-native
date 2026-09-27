import { createApp, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';

import { initStores, useAccessStore } from '@vben/stores';

import { afterEach, expect, it, vi } from 'vitest';

import TableAction from '../../dushan-admin-frontend/apps/web-ele/src/components/table-action/table-action.vue';
import { setupSession } from '../../dushan-admin-frontend/apps/web-ele/src/services/session/runtime';
import { useAuthStore } from '../../dushan-admin-frontend/apps/web-ele/src/store/auth';

const stubs = vi.hoisted(() => ({ info: vi.fn(), login: vi.fn() }));
vi.mock('#/api', () => ({
  getPermissionInfoApi: stubs.info,
  loginApi: stubs.login,
  logoutApi: vi.fn(),
  smsLoginApi: vi.fn(),
  registerApi: vi.fn(),
  socialLoginApi: vi.fn(),
}));
vi.mock('#/locales', () => ({ $t: (key: string) => key }));
const cleanups: Array<() => void> = [];
const permissions = [
  'system:user:create',
  'system:user:update',
  'system:user:delete',
];

afterEach(() => {
  for (const close of cleanups.splice(0)) close();
  localStorage.clear();
});

async function fixture() {
  localStorage.clear();
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { render: () => null } },
      { path: '/home', component: { render: () => null } },
    ],
  });
  const element = document.createElement('div');
  const app = createApp(() =>
    h(TableAction, {
      actions: [
        { label: '新增用户', auth: ['system:user:create'], onClick: vi.fn() },
        { label: '编辑用户', auth: ['system:user:update'], onClick: vi.fn() },
        {
          label: '未授予操作',
          auth: ['system:user:ungranted'],
          onClick: vi.fn(),
        },
      ],
    }),
  );
  await initStores(app, { namespace: 'session-permissions-test' });
  app.use(router);
  await router.push('/');
  await router.isReady();
  const session = setupSession({
    namespace: 'session-permissions-test',
    expire: async () => {},
    refresh: async () => 'refreshed-token',
  });
  const auth = app.runWithContext(() => useAuthStore());
  app.mount(element);
  cleanups.push(() => {
    session.dispose();
    app.unmount();
  });
  stubs.login.mockResolvedValue({ accessToken: 'new-token', tenantId: '1' });
  stubs.info.mockResolvedValue({
    tenantId: '1',
    menus: [],
    permissions,
    user: {
      userId: '101',
      username: 'admin',
      realName: '',
      roles: ['super_admin'],
      homePath: '/home',
      avatar: '',
      desc: '',
      token: '',
    },
  });
  return { auth, access: useAccessStore(), session, element };
}

it('读取当前会话不能用旧的持久化快照覆盖刚取得的操作权限', async () => {
  const { access, session, element } = await fixture();
  session.replace('current-token');
  access.setAccessCodes(permissions);
  session.capture();
  expect(access.accessCodes).toEqual(permissions);
  await nextTick();
  expect(element.textContent).toContain('新增用户');
  expect(element.textContent).toContain('编辑用户');
  expect(element.textContent).not.toContain('未授予操作');
});

it('真实持久化Store与认证流程完成后，操作按钮持续可见', async () => {
  const { auth, access, session, element } = await fixture();
  await auth.authLogin({ username: 'admin', password: 'test-password' });
  session.capture();
  await nextTick();
  expect(access.accessCodes).toEqual(permissions);
  expect(element.textContent).toContain('新增用户');
  expect(element.textContent).toContain('编辑用户');
});

it('服务端收回操作权限后不会从旧缓存恢复按钮', async () => {
  const { auth, access, session, element } = await fixture();
  await auth.authLogin({ username: 'admin', password: 'test-password' });
  await nextTick();
  access.setAccessCodes([]);
  session.capture();
  await nextTick();
  expect(access.accessCodes).toEqual([]);
  expect(element.textContent).not.toContain('新增用户');
  expect(element.textContent).not.toContain('编辑用户');
});
