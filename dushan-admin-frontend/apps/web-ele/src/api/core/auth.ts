import type { UserInfo } from '@vben/types';

import type { MenuNode } from '../../router/menu-adapter';

import { z } from '@vben/common-ui';
import { preferences } from '@vben/preferences';

import { authenticationClient, requestClient } from '#/api/request';

import { parseBackendMenus } from '../../router/backend-menu';
import { readRedirect } from '../../router/session-access';

export namespace AuthApi {
  /** 登录接口参数 */
  export interface LoginParams {
    password?: string;
    username?: string;
    verification?: null | string;
  }

  /** 登录接口返回值 */
  export interface LoginResult {
    accessToken: string;
  }
}

/** 登录用户的身份、角色、权限码与授权菜单，由后端一次返回。 */
export interface PermissionInfo {
  menus: MenuNode[];
  permissions: string[];
  user: UserInfo;
}

/** 只声明前端消费的字段；后端其余字段（deptId、email 等）在此丢弃。 */
const permissionInfoSchema = z.object({
  menus: z.array(z.unknown()),
  permissions: z.array(z.string().min(1)),
  roles: z.array(z.string().min(1)),
  user: z.object({
    avatar: z.string(),
    id: z.string().min(1),
    nickname: z.string(),
    username: z.string().min(1),
  }),
});

/**
 * 登录
 */
export async function loginApi(data: AuthApi.LoginParams) {
  if (
    typeof data.username !== 'string' ||
    data.username.length === 0 ||
    typeof data.password !== 'string' ||
    data.password.length === 0
  )
    throw new TypeError('登录需要用户名和密码');
  if (
    data.verification !== undefined &&
    data.verification !== null &&
    typeof data.verification !== 'string'
  )
    throw new TypeError('验证码结果必须是字符串或 null');
  const result = await requestClient.post<AuthApi.LoginResult>(
    '/system/auth/login',
    {
      username: data.username,
      password: data.password,
      verification: data.verification,
    },
  );
  if (typeof result.accessToken !== 'string' || result.accessToken.length === 0)
    throw new TypeError('登录接口必须返回非空令牌');
  return result;
}

/**
 * 刷新accessToken
 */
export async function refreshTokenApi(signal: AbortSignal) {
  const result = await authenticationClient.post<AuthApi.LoginResult>(
    '/system/auth/refresh-token',
    undefined,
    {
      signal,
      withCredentials: true,
    },
  );
  if (typeof result.accessToken !== 'string' || result.accessToken.length === 0)
    throw new TypeError('刷新接口必须返回非空令牌');
  return result.accessToken;
}

/**
 * 退出登录
 *
 * 后端只在请求带 Authorization 时撤销会话族，因此由调用方传入当前令牌；
 * 该客户端不安装会话拦截器，退出失败不会触发刷新。
 */
export async function logoutApi(token: string) {
  return authenticationClient.post('/system/auth/logout', undefined, {
    headers: { Authorization: `Bearer ${token}` },
    withCredentials: true,
  });
}

/**
 * 获取登录用户的权限信息：身份、角色、权限码与授权菜单
 *
 * 后端同一响应提供四者，避免三次请求之间权限变更产生不一致组合。
 * `homePath` 后端不提供，由应用偏好决定。
 */
export async function getPermissionInfoApi(): Promise<PermissionInfo> {
  const body = permissionInfoSchema.parse(
    await requestClient.get<unknown>('/system/auth/get-permission-info'),
  );
  const homePath = preferences.app.defaultHomePath;
  readRedirect(homePath, '');
  return {
    menus: parseBackendMenus(body.menus),
    permissions: body.permissions,
    user: {
      avatar: body.user.avatar,
      desc: '',
      homePath,
      realName: body.user.nickname,
      roles: body.roles,
      token: '',
      userId: body.user.id,
      username: body.user.username,
    },
  };
}
