import type { UserInfo } from '@vben/types';

import type { MenuNode } from '../../router/menu-adapter';

import type { NativeRequestConfig } from '#/api/response';

import { z } from '@vben/common-ui';
import { preferences } from '@vben/preferences';

import {
  anonymousClient,
  authenticationClient,
  requestClient,
} from '#/api/request';

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
    tenantId: string;
  }

  export interface SmsLoginParams {
    mobile: string;
    code: string;
  }

  export interface RegisterParams {
    username: string;
    nickname: string;
    password: string;
    verification?: null | string;
  }

  export interface SocialLoginParams {
    type: number;
    code: string;
    state: string;
  }

  export interface SocialProvider {
    type: number;
    name: string;
    source: string;
    mode: 'browser' | 'native';
    codeParameter: string;
  }

  export interface SmsSendParams {
    mobile: string;
    verification?: null | string;
  }

  export type RecoveryTarget =
    | { channel: 'email'; email: string }
    | { channel: 'sms'; mobile: string };

  export interface TenantConfig {
    enabled: boolean;
    tenants: { id: string; name: string }[];
  }
}

const tenantConfigSchema = z.object({
  enabled: z.boolean(),
  tenants: z.array(
    z.object({ id: z.string().min(1), name: z.string().min(1) }),
  ),
});

export async function getLoginTenantsApi(): Promise<AuthApi.TenantConfig> {
  return tenantConfigSchema.parse(
    await authenticationClient.get('/system/auth/tenants'),
  );
}

export async function getSocialProvidersApi(tenantId?: string) {
  const config: NativeRequestConfig = {
    ...tenantRequest(tenantId),
    errorMessageMode: 'form',
  };
  return z
    .array(
      z.object({
        type: z.number().int().positive(),
        name: z.string().min(1),
        source: z.string().regex(/^[A-Z][A-Z0-9_]*$/),
        mode: z.literal('browser'),
        codeParameter: z.string().regex(/^[a-zA-Z][a-zA-Z0-9_]*$/),
      }),
    )
    .parse(await anonymousClient.get('/system/auth/social-providers', config));
}

export async function socialAuthRedirectApi(
  type: number,
  redirectUri: string,
  tenantId?: string,
) {
  return z
    .string()
    .url()
    .parse(
      await anonymousClient.post(
        '/system/auth/social-auth-redirect',
        undefined,
        {
          ...tenantRequest(tenantId),
          params: { type, redirectUri },
        },
      ),
    );
}

export async function socialLoginApi(data: AuthApi.SocialLoginParams) {
  const config: NativeRequestConfig = {
    withCredentials: true,
    errorMessageMode: 'form',
  };
  return validateLoginResult(
    await anonymousClient.post<AuthApi.LoginResult>(
      '/system/auth/social-login',
      data,
      config,
    ),
  );
}

/** 注册入口需双端开启；无法取得服务端许可时保持关闭。 */
export async function isRegistrationEnabled(): Promise<boolean> {
  if (import.meta.env.VITE_APP_REGISTER_ENABLE !== 'true') return false;
  try {
    return z
      .boolean()
      .parse(
        await authenticationClient.get('/system/auth/registration-enabled'),
      );
  } catch {
    return false;
  }
}

export async function registerApi(
  data: AuthApi.RegisterParams,
  tenantId?: string,
) {
  return validateLoginResult(
    await anonymousClient.post<AuthApi.LoginResult>(
      '/system/auth/register',
      {
        username: data.username,
        nickname: data.nickname,
        password: data.password,
        verification: data.verification,
      },
      tenantRequest(tenantId),
    ),
  );
}

/** 登录用户的身份、角色、权限码与授权菜单，由后端一次返回。 */
export interface PermissionInfo {
  tenantId: string;
  menus: MenuNode[];
  permissions: string[];
  user: UserInfo;
}

/** 只声明前端消费的字段；后端其余字段（deptId、email 等）在此丢弃。 */
const permissionInfoSchema = z.object({
  tenantId: z.string().min(1),
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
export async function loginApi(data: AuthApi.LoginParams, tenantId?: string) {
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
  const result = await anonymousClient.post<AuthApi.LoginResult>(
    '/system/auth/login',
    {
      username: data.username,
      password: data.password,
      verification: data.verification,
    },
    tenantRequest(tenantId),
  );
  return validateLoginResult(result);
}

function validateLoginResult(result: AuthApi.LoginResult) {
  if (typeof result.accessToken !== 'string' || result.accessToken.length === 0)
    throw new TypeError('登录接口必须返回非空令牌');
  if (typeof result.tenantId !== 'string' || result.tenantId.length === 0)
    throw new TypeError('登录接口必须返回实际租户');
  return result;
}

export async function smsLoginApi(
  data: AuthApi.SmsLoginParams,
  tenantId?: string,
) {
  return validateLoginResult(
    await anonymousClient.post<AuthApi.LoginResult>(
      '/system/auth/sms-login',
      data,
      tenantRequest(tenantId),
    ),
  );
}

export async function sendLoginSmsApi(
  data: AuthApi.SmsSendParams,
  tenantId?: string,
): Promise<number> {
  const result = await anonymousClient.post<unknown>(
    '/system/auth/send-sms-code',
    {
      ...data,
      scene: 21,
    },
    tenantRequest(tenantId),
  );
  return z.number().int().min(4).max(6).parse(result);
}

export async function sendRecoveryCodeApi(
  data: AuthApi.RecoveryTarget & { verification?: null | string },
  tenantId?: string,
) {
  return z
    .number()
    .int()
    .min(4)
    .max(6)
    .parse(
      await anonymousClient.post(
        '/system/auth/send-password-reset-code',
        data,
        tenantRequest(tenantId),
      ),
    );
}

export async function resetPasswordApi(
  data: AuthApi.RecoveryTarget & { code: string; password: string },
  tenantId?: string,
) {
  return z
    .literal(true)
    .parse(
      await anonymousClient.post(
        '/system/auth/reset-password',
        data,
        tenantRequest(tenantId),
      ),
    );
}

function tenantRequest(tenantId?: string) {
  return {
    headers: tenantId === undefined ? {} : { 'X-Tenant-Id': tenantId },
    withCredentials: true,
  };
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
    tenantId: body.tenantId,
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
