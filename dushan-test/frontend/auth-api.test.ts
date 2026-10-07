import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const calls = vi.hoisted(
  () =>
    [] as Array<{
      client: 'anonymous' | 'authentication' | 'request';
      config?: Record<string, unknown>;
      data?: unknown;
      method: string;
      url: string;
    }>,
);
const replies = vi.hoisted(() => ({ value: undefined as unknown }));

function client(name: 'anonymous' | 'authentication' | 'request') {
  const record =
    (method: string) =>
    (url: string, data?: unknown, config?: Record<string, unknown>) => {
      // get(url, config) 与 post(url, data, config) 的签名不同，按实参归位。
      calls.push(
        method === 'get'
          ? {
              client: name,
              config: data as Record<string, unknown>,
              method,
              url,
            }
          : { client: name, config, data, method, url },
      );
      return Promise.resolve(replies.value);
    };
  return { get: record('get'), post: record('post') };
}

vi.mock('#/api/request', () => ({
  anonymousClient: client('anonymous'),
  authenticationClient: client('authentication'),
  requestClient: client('request'),
}));

const {
  getLoginTenantsApi,
  getSocialProvidersApi,
  socialAuthRedirectApi,
  socialLoginApi,
  isRegistrationEnabled,
  registerApi,
  getPermissionInfoApi,
  loginApi,
  logoutApi,
  refreshTokenApi,
  sendLoginSmsApi,
  smsLoginApi,
  sendRecoveryCodeApi,
  resetPasswordApi,
} = await import('../../dushan-admin-frontend/apps/web-ele/src/api/core/auth');
const { getDictionaryDataApi } =
  await import('../../dushan-admin-frontend/apps/web-ele/src/api/core/dictionary');

function permissionInfoBody() {
  return {
    tenantId: '1',
    menus: [
      {
        alwaysShow: true,
        children: null,
        component: 'system/user/index',
        componentName: 'SystemUser',
        dataPermission: false,
        icon: 'ep:user',
        id: '10000000000101',
        keepAlive: true,
        kind: 'page',
        name: '用户管理',
        parentId: '0',
        path: '/user',
        url: null,
        visible: true,
      },
    ],
    permissions: ['system:user:query'],
    roles: ['super_admin'],
    user: {
      avatar: '',
      deptId: '10000000000001',
      email: null,
      id: '10000000000001',
      nickname: '渡山管理员',
      username: 'admin',
    },
  };
}

beforeEach(() => {
  calls.length = 0;
  replies.value = undefined;
});

afterEach(() => vi.unstubAllEnvs());

describe('核心接口与后端真实端点对齐', () => {
  it('渠道与授权跳转发送所选租户，回调只带浏览器Cookie且不带租户头', async () => {
    replies.value = [
      {
        type: 20,
        source: 'DINGTALK',
        name: '钉钉',
        mode: 'browser',
        codeParameter: 'code',
      },
    ];
    await expect(getSocialProvidersApi('2')).resolves.toEqual(replies.value);
    expect(calls[0]).toMatchObject({
      client: 'anonymous',
      url: '/system/auth/social-providers',
      config: { headers: { 'X-Tenant-Id': '2' } },
    });
    replies.value = 'https://vendor.example/authorize?state=generated';
    await socialAuthRedirectApi(
      20,
      'https://app.example/auth/social-login',
      '2',
    );
    expect(calls[1]).toMatchObject({
      client: 'anonymous',
      method: 'post',
      config: {
        headers: { 'X-Tenant-Id': '2' },
        withCredentials: true,
        params: {
          type: 20,
          redirectUri: 'https://app.example/auth/social-login',
        },
      },
    });
    replies.value = { accessToken: 'social-token', tenantId: '2' };
    await socialLoginApi({ type: 20, code: 'code', state: 'state' });
    expect(calls[2]).toMatchObject({
      client: 'anonymous',
      url: '/system/auth/social-login',
      config: { withCredentials: true, errorMessageMode: 'form' },
    });
    expect(calls[2]?.config).not.toHaveProperty('headers');
  });
  it.each([
    ['false', false, false],
    ['false', true, false],
    ['true', false, false],
    ['true', true, true],
    [undefined, true, false],
    ['true', 'true', false],
  ])(
    '注册入口要求双端明确开启：%s / %s',
    async (frontend, backend, enabled) => {
      vi.stubEnv('VITE_APP_REGISTER_ENABLE', frontend);
      replies.value = backend;
      await expect(isRegistrationEnabled()).resolves.toBe(enabled);
      expect(calls).toHaveLength(frontend === 'true' ? 1 : 0);
    },
  );

  it('注册配置请求失败时保持关闭', async () => {
    vi.stubEnv('VITE_APP_REGISTER_ENABLE', 'true');
    replies.value = Promise.reject(new Error('offline'));
    await expect(isRegistrationEnabled()).resolves.toBe(false);
  });

  it('注册只提交声明字段，租户在请求头传递并接收真实会话', async () => {
    replies.value = { accessToken: 'registered', tenantId: '2' };
    const params = {
      username: 'newuser',
      nickname: 'New',
      password: 'Password123',
      verification: 'proof',
      confirmPassword: 'Password123',
      tenantId: 'wrong',
    };
    await expect(registerApi(params, '2')).resolves.toEqual(replies.value);
    expect(calls[0]).toEqual({
      client: 'anonymous',
      method: 'post',
      url: '/system/auth/register',
      config: { headers: { 'X-Tenant-Id': '2' }, withCredentials: true },
      data: {
        username: 'newuser',
        nickname: 'New',
        password: 'Password123',
        verification: 'proof',
      },
    });
  });
  it('找回密码的短信和邮箱渠道使用同一协议，确认密码不提交', async () => {
    replies.value = 6;
    await expect(
      sendRecoveryCodeApi(
        {
          channel: 'email',
          email: 'user@example.com',
          verification: 'proof',
        },
        '2',
      ),
    ).resolves.toBe(6);
    expect(calls[0]).toMatchObject({
      client: 'anonymous',
      config: { headers: { 'X-Tenant-Id': '2' } },
      url: '/system/auth/send-password-reset-code',
      data: {
        channel: 'email',
        email: 'user@example.com',
        verification: 'proof',
      },
    });
    replies.value = true;
    await expect(
      resetPasswordApi(
        {
          channel: 'sms',
          mobile: '13800001001',
          code: '1234',
          password: 'Changed123',
        },
        '2',
      ),
    ).resolves.toBe(true);
    expect(calls[1]).toMatchObject({
      client: 'anonymous',
      config: { headers: { 'X-Tenant-Id': '2' } },
      url: '/system/auth/reset-password',
      data: {
        channel: 'sms',
        mobile: '13800001001',
        code: '1234',
        password: 'Changed123',
      },
    });
  });

  it('短信发送带登录场景和人机验证凭证，返回实际验证码长度', async () => {
    replies.value = 4;
    await expect(
      sendLoginSmsApi(
        {
          mobile: '13800001001',
          verification: 'proof',
        },
        '2',
      ),
    ).resolves.toBe(4);
    expect(calls[0]).toMatchObject({
      client: 'anonymous',
      config: { headers: { 'X-Tenant-Id': '2' } },
      url: '/system/auth/send-sms-code',
      data: {
        mobile: '13800001001',
        scene: 21,
        verification: 'proof',
      },
    });
  });

  it('手机号登录复用服务端令牌与租户响应契约', async () => {
    replies.value = { accessToken: 'sms-token', tenantId: '2' };
    await expect(
      smsLoginApi({ mobile: '13800001001', code: '8888' }, '2'),
    ).resolves.toEqual(replies.value);
    expect(calls[0]).toMatchObject({
      client: 'anonymous',
      config: { headers: { 'X-Tenant-Id': '2' } },
      url: '/system/auth/sms-login',
      data: { mobile: '13800001001', code: '8888' },
    });
  });

  it('登录前匿名取得租户开关与精简列表', async () => {
    replies.value = {
      enabled: true,
      tenants: [{ id: '9223372036854775807', name: 'Tenant B' }],
    };
    await expect(getLoginTenantsApi()).resolves.toEqual(replies.value);
    expect(calls[0]).toMatchObject({
      client: 'authentication',
      method: 'get',
      url: '/system/auth/tenants',
    });
  });

  it('所选租户以字符串提交，响应使用服务端确认的租户', async () => {
    replies.value = { accessToken: 'token-b', tenantId: '9223372036854775807' };
    await expect(
      loginApi(
        {
          username: 'admin',
          password: 'TenantB123',
        },
        '9223372036854775807',
      ),
    ).resolves.toEqual(replies.value);
    expect(calls[0]?.config).toMatchObject({
      headers: { 'X-Tenant-Id': '9223372036854775807' },
    });
    expect(calls[0]?.data).not.toHaveProperty('tenantId');
  });

  it('登录打 /system/auth/login，只送后端声明的三个字段', async () => {
    replies.value = {
      accessToken: 'token-1',
      tenantId: '1',
      expiresTime: 1,
      userId: '1',
    };
    await expect(
      loginApi({ password: 'admin123', username: 'admin' }),
    ).resolves.toMatchObject({ accessToken: 'token-1' });
    expect(calls).toEqual([
      {
        client: 'anonymous',
        config: { headers: {}, withCredentials: true },
        data: {
          password: 'admin123',
          username: 'admin',
          verification: undefined,
        },
        method: 'post',
        url: '/system/auth/login',
      },
    ]);
  });

  it('刷新打 /system/auth/refresh-token，从对象里取 accessToken 并携带凭据', async () => {
    replies.value = { accessToken: 'token-2', expiresTime: 2, userId: '1' };
    const signal = new AbortController().signal;
    await expect(refreshTokenApi(signal)).resolves.toBe('token-2');
    expect(calls[0]).toMatchObject({
      client: 'authentication',
      config: { signal, withCredentials: true },
      method: 'post',
      url: '/system/auth/refresh-token',
    });
  });

  it('刷新返回空令牌或缺字段时报协议错误，不把无效令牌写回会话', async () => {
    const signal = new AbortController().signal;
    for (const body of [{ accessToken: '' }, {}, 'token-as-string']) {
      replies.value = body;
      await expect(refreshTokenApi(signal)).rejects.toThrow(
        '刷新接口必须返回非空令牌',
      );
    }
  });

  it('退出带 Authorization，后端据此撤销会话族', async () => {
    replies.value = true;
    await logoutApi('token-3');
    expect(calls[0]).toMatchObject({
      client: 'authentication',
      config: {
        headers: { Authorization: 'Bearer token-3' },
        withCredentials: true,
      },
      method: 'post',
      url: '/system/auth/logout',
    });
  });

  it('权限信息一次取回并投影为 Vben UserInfo，homePath 由应用偏好提供', async () => {
    replies.value = permissionInfoBody();
    const info = await getPermissionInfoApi();
    expect(calls[0]).toMatchObject({
      client: 'request',
      method: 'get',
      url: '/system/auth/get-permission-info',
    });
    expect(info.user).toEqual({
      avatar: '',
      desc: '',
      homePath: '/dashboard',
      realName: '渡山管理员',
      roles: ['super_admin'],
      token: '',
      userId: '10000000000001',
      username: 'admin',
    });
    expect(info.permissions).toEqual(['system:user:query']);
    expect(info.menus).toMatchObject([
      { component: '/system/user/index.vue', order: 0, title: '用户管理' },
    ]);
  });

  it('权限信息缺少必填字段时报协议错误，不产生半个登录态', async () => {
    for (const body of [
      { ...permissionInfoBody(), roles: [''] },
      { ...permissionInfoBody(), user: { id: '1' } },
      { ...permissionInfoBody(), permissions: ['ok', 1] },
      { ...permissionInfoBody(), menus: [{ id: '1' }] },
      null,
    ]) {
      replies.value = body;
      // 协议校验失败即 zod 解析错误；测试目录不解析 @vben/common-ui，按错误名断言。
      await expect(getPermissionInfoApi()).rejects.toThrow(
        expect.objectContaining({ name: 'ZodError' }),
      );
    }
  });

  it('字典打 /system/dict/data/simple-list 并透传取消信号', async () => {
    replies.value = [];
    const signal = new AbortController().signal;
    await getDictionaryDataApi(signal);
    expect(calls[0]).toMatchObject({
      client: 'request',
      config: { signal },
      method: 'get',
      url: '/system/dict/data/simple-list',
    });
  });
});
