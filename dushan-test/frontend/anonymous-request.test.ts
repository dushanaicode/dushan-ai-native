import { beforeEach, expect, it, vi } from 'vitest';

const state = vi.hoisted(() => ({ session: vi.fn(), message: vi.fn() }));
vi.mock('@vben/hooks', () => ({
  useAppConfig: () => ({ apiURL: 'http://testserver/admin-api' }),
}));
vi.mock('@vben/preferences', () => ({
  preferences: { app: { locale: 'zh-CN', enableRefreshToken: true } },
}));
vi.mock('element-plus', () => ({ ElMessage: { error: state.message } }));
vi.mock(
  '../../dushan-admin-frontend/apps/web-ele/src/services/session/runtime',
  () => ({ getSession: state.session }),
);

const { anonymousClient } =
  await import('../../dushan-admin-frontend/apps/web-ele/src/api/request');

beforeEach(() => {
  vi.clearAllMocks();
  state.session.mockImplementation(() => {
    throw new Error('anonymous request touched the session');
  });
});

it('匿名客户端保留租户头和业务正文，不附加旧登录令牌', async () => {
  const body = { username: 'admin', password: 'test-only' };
  let sent: any;
  await expect(
    anonymousClient.post('/system/auth/login', body, {
      headers: { 'X-Tenant-Id': '2' },
      adapter: async (config: any) => {
        sent = config;
        return {
          config,
          status: 200,
          statusText: 'OK',
          headers: {},
          data: { code: 0, message: '', data: { ok: true }, error: null },
        };
      },
    }),
  ).resolves.toEqual({ ok: true });
  expect(sent.headers.get('X-Tenant-Id')).toBe('2');
  expect(sent.headers.get('Authorization')).toBeUndefined();
  expect(JSON.parse(sent.data)).toEqual(body);
  expect(state.session).not.toHaveBeenCalled();
});

it('匿名认证失败不会刷新或清除已有会话', async () => {
  await expect(
    anonymousClient.post(
      '/system/auth/login',
      {},
      {
        adapter: async (config: any) => ({
          config,
          status: 200,
          statusText: 'OK',
          headers: {},
          data: { code: 401, message: 'expired', data: null, error: null },
        }),
      },
    ),
  ).rejects.toMatchObject({ message: 'expired' });
  expect(state.session).not.toHaveBeenCalled();
});
