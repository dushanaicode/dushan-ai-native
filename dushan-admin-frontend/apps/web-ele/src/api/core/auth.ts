import { authenticationClient, requestClient } from '#/api/request';

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
  const result = await requestClient.post<AuthApi.LoginResult>('/auth/login', {
    username: data.username,
    password: data.password,
    verification: data.verification,
  });
  if (typeof result.accessToken !== 'string' || result.accessToken.length === 0)
    throw new TypeError('登录接口必须返回非空令牌');
  return result;
}

/**
 * 刷新accessToken
 */
export async function refreshTokenApi(signal: AbortSignal) {
  const token = await authenticationClient.post<unknown>(
    '/auth/refresh',
    undefined,
    {
      signal,
      withCredentials: true,
    },
  );
  if (typeof token !== 'string' || token.length === 0)
    throw new TypeError('刷新接口必须返回非空令牌');
  return token;
}

/**
 * 退出登录
 */
export async function logoutApi() {
  return authenticationClient.post('/auth/logout', undefined, {
    withCredentials: true,
  });
}

/**
 * 获取用户权限码
 */
export async function getAccessCodesApi() {
  const codes = await requestClient.get<unknown>('/auth/codes');
  if (!Array.isArray(codes) || !codes.every((code) => typeof code === 'string'))
    throw new TypeError('权限码必须是字符串数组');
  return codes as string[];
}
