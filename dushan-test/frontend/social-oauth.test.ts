import { afterEach, beforeEach, expect, it, vi } from 'vitest';

import {
  beginSocialOAuth,
  consumeSocialContext,
  socialCallbackCode,
  socialCallbackUri,
} from '../../dushan-admin-frontend/apps/web-ele/src/views/_core/authentication/social-oauth';

const stubs = vi.hoisted(() => ({ redirect: vi.fn() }));
vi.mock('#/api/core/auth', () => ({ socialAuthRedirectApi: stubs.redirect }));
beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
  vi.stubEnv('BASE_URL', '/admin/');
});
afterEach(() => {
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

it('跳转前只保存按state索引的流程信息，读取一次后删除', async () => {
  stubs.redirect.mockResolvedValue(
    'https://oapi.dingtalk.com/connect/qrconnect?state=one-time',
  );
  const navigate = vi
    .spyOn(window.location, 'assign')
    .mockImplementation(() => {});
  const context = {
    type: 20,
    codeParameter: 'code',
    tenantId: '9223372036854775807',
    returnPath: '/workbench',
  };
  await beginSocialOAuth(context);
  expect(stubs.redirect).toHaveBeenCalledWith(
    20,
    socialCallbackUri(),
    context.tenantId,
  );
  expect(socialCallbackUri()).toContain('/admin/auth/social-login');
  expect(navigate).toHaveBeenCalledOnce();
  expect(consumeSocialContext('one-time')).toEqual(context);
  expect(() => consumeSocialContext('one-time')).toThrow();
});

it.each([
  'javascript:alert(1)',
  'https://vendor.example/no-state',
  'https://vendor.example/?state=a&state=b',
])('拒绝不符合授权契约的URL：%s', async (url) => {
  stubs.redirect.mockResolvedValue(url);
  const navigate = vi
    .spyOn(window.location, 'assign')
    .mockImplementation(() => {});
  await expect(
    beginSocialOAuth({ type: 30, codeParameter: 'code', returnPath: '' }),
  ).rejects.toThrow();
  expect(navigate).not.toHaveBeenCalled();
  expect(sessionStorage.length).toBe(0);
});

it('拒绝外站返回地址和未知state，回调参数重复或选错渠道时拒绝', async () => {
  await expect(
    beginSocialOAuth({
      type: 20,
      codeParameter: 'code',
      returnPath: '//evil.example',
    }),
  ).rejects.toThrow();
  expect(stubs.redirect).not.toHaveBeenCalled();
  expect(() => consumeSocialContext('unknown')).toThrow();
  expect(socialCallbackCode('code', { code: 'ding-code' })).toBe('ding-code');
  expect(socialCallbackCode('authCode', { authCode: 'ding-v2' })).toBe(
    'ding-v2',
  );
  expect(socialCallbackCode('auth_code', { auth_code: 'alipay-code' })).toBe(
    'alipay-code',
  );
  expect(() => socialCallbackCode('code', { code: ['a', 'b'] })).toThrow();
  expect(() =>
    socialCallbackCode('auth_code', { code: 'wrong-parameter' }),
  ).toThrow();
});
