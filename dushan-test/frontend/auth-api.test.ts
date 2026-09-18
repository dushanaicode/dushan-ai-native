import { beforeEach, describe, expect, it, vi } from 'vitest';

const calls = vi.hoisted(
  () =>
    [] as Array<{
      client: 'authentication' | 'request';
      config?: Record<string, unknown>;
      data?: unknown;
      method: string;
      url: string;
    }>,
);
const replies = vi.hoisted(() => ({ value: undefined as unknown }));

function client(name: 'authentication' | 'request') {
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
  authenticationClient: client('authentication'),
  requestClient: client('request'),
}));

const { getPermissionInfoApi, loginApi, logoutApi, refreshTokenApi } =
  await import('../../dushan-admin-frontend/apps/web-ele/src/api/core/auth');
const { getDictionaryDataApi } =
  await import('../../dushan-admin-frontend/apps/web-ele/src/api/core/dictionary');

function permissionInfoBody() {
  return {
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

describe('核心接口与后端真实端点对齐', () => {
  it('登录打 /system/auth/login，只送后端声明的三个字段', async () => {
    replies.value = { accessToken: 'token-1', expiresTime: 1, userId: '1' };
    await expect(
      loginApi({ password: 'admin123', username: 'admin' }),
    ).resolves.toMatchObject({ accessToken: 'token-1' });
    expect(calls).toEqual([
      {
        client: 'request',
        config: undefined,
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
