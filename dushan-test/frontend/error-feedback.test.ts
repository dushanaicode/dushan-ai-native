import type { SessionSnapshot } from '../../dushan-admin-frontend/apps/web-ele/src/services/session/coordinator';

import { AxiosError } from '@vben/request';

import { beforeEach, expect, it, vi } from 'vitest';

import { BusinessError } from '../../dushan-admin-frontend/apps/web-ele/src/api/business-error';
import {
  getErrorMessage,
  notifyError,
  takeErrorMessage,
} from '../../dushan-admin-frontend/apps/web-ele/src/api/error-feedback';
import {
  anonymousClient,
  authenticationClient,
  requestClient,
} from '../../dushan-admin-frontend/apps/web-ele/src/api/request';
import {
  SessionChangedError,
  SessionCoordinator,
} from '../../dushan-admin-frontend/apps/web-ele/src/services/session/coordinator';
import { getWebSocketTicket } from '../../dushan-admin-frontend/apps/web-ele/src/services/realtime-ports';

const stubs = vi.hoisted(() => ({
  message: vi.fn(),
  session: vi.fn(),
  preferences: { app: { locale: 'zh-CN', enableRefreshToken: false } },
}));
vi.mock('@vben/hooks', () => ({
  useAppConfig: () => ({ apiURL: 'http://testserver/admin-api' }),
}));
vi.mock('@vben/preferences', () => ({
  preferences: stubs.preferences,
}));
vi.mock('element-plus', () => ({ ElMessage: { error: stubs.message } }));
vi.mock('#/services/session/runtime', () => ({ getSession: stubs.session }));
beforeEach(() => {
  vi.clearAllMocks();
  stubs.preferences.app.enableRefreshToken = false;
  stubs.session.mockReturnValue({
    capture: () => ({ generation: 'one', token: 'token' }),
    assertCurrent: (scope: unknown) => scope,
  });
});
const body = {
  code: 1002002,
  message: '后端具体原因',
  data: null,
  error: null,
};

it.each([401, 200])(
  'WebSocket取票认证过期（HTTP %s）自动刷新重试，无错误提示',
  async (status) => {
    let stored: SessionSnapshot = { generation: 'ticket', token: 'old' };
    const refresh = vi.fn(async () => 'new');
    const expire = vi.fn(async () => {});
    const session = new SessionCoordinator({
      read: () => stored,
      write: (value) => {
        stored = value;
      },
      refresh,
      expire,
      lock: (run) => run(),
      subscribe: () => () => {},
    });
    stubs.session.mockReturnValue(session);
    stubs.preferences.app.enableRefreshToken = true;
    const adapter = vi.fn(async (config) => {
      const valid = config.headers.Authorization === 'Bearer new';
      const response = {
        config,
        status: valid ? 200 : status,
        statusText: valid ? 'OK' : 'Unauthorized',
        headers: {},
        data: {
          code: valid ? 0 : 1004003,
          message: valid ? '' : '访问凭据已过期',
          data: valid ? 'fresh-ticket' : null,
          error: null,
        },
      };
      if (!valid && status === 401)
        throw new AxiosError(
          'Unauthorized',
          'ERR_BAD_REQUEST',
          config,
          undefined,
          response,
        );
      return response;
    });
    const original = requestClient.post.bind(requestClient);
    const post = vi
      .spyOn(requestClient, 'post')
      .mockImplementation((url, data, config) =>
        original(url, data, { ...config, adapter }),
      );
    try {
      const ticket = await getWebSocketTicket(new AbortController().signal);
      expect(ticket.ticket).toBe('fresh-ticket');
      expect(ticket.expiresAtMs).toBeGreaterThan(Date.now());
      expect(refresh).toHaveBeenCalledOnce();
      expect(adapter).toHaveBeenCalledTimes(2);
      expect(stubs.message).not.toHaveBeenCalled();
      expect(expire).not.toHaveBeenCalled();
    } finally {
      post.mockRestore();
      session.dispose();
    }
  },
);

it.each(['post', 'put', 'delete'] as const)(
  'Native过期拒绝后%s续期重试，不留下局部横幅或全局提示',
  async (method) => {
    let stored: SessionSnapshot = { generation: 'silent', token: 'old' };
    const refresh = vi.fn(async () => 'new');
    const expired = vi.fn(async () => {});
    const session = new SessionCoordinator({
      read: () => stored,
      write: (snapshot) => {
        stored = snapshot;
      },
      lock: (operation) => operation(),
      subscribe: () => () => {},
      refresh,
      expire: expired,
    });
    stubs.session.mockReturnValue(session);
    stubs.preferences.app.enableRefreshToken = true;
    let executed = 0;
    let banner = '';
    let result: unknown;
    const adapter = vi.fn(async (config) => {
      const authorized = config.headers.Authorization === 'Bearer new';
      if (authorized) executed++;
      return {
        config,
        status: 200,
        statusText: 'OK',
        headers: {},
        data: {
          code: authorized ? 0 : 1004003,
          message: authorized ? '' : '访问凭据已过期',
          data: authorized ? 'done' : null,
          error: null,
        },
      };
    });
    try {
      result = await requestClient.request('/native-write', {
        method,
        data: { value: 1 },
        adapter,
        errorMessageMode: 'form',
      });
    } catch (error) {
      banner = takeErrorMessage(error, '操作失败');
    } finally {
      session.dispose();
    }
    expect(banner).toBe('');
    expect(result).toBe('done');
    expect(refresh).toHaveBeenCalledOnce();
    expect(adapter).toHaveBeenCalledTimes(2);
    expect(executed).toBe(1);
    expect(adapter.mock.calls[1]![0].data).toEqual(
      adapter.mock.calls[0]![0].data,
    );
    expect(stubs.message).not.toHaveBeenCalled();
    expect(expired).not.toHaveBeenCalled();
  },
);

it.each([anonymousClient, requestClient])(
  '全局展示后，组件横幅和页面catch不重复提示',
  async (client) => {
    let failure: unknown;
    try {
      await client.get('/failure', {
        adapter: async (config) => ({
          config,
          data: body,
          status: 200,
          statusText: 'OK',
          headers: {},
        }),
      });
    } catch (error) {
      failure = error;
    }
    expect(failure).toBeInstanceOf(BusinessError);
    expect(stubs.message).toHaveBeenCalledExactlyOnceWith('后端具体原因');
    expect(takeErrorMessage(failure, '页面固定失败')).toBe('');
    notifyError(failure, '又一条固定失败');
    expect(stubs.message).toHaveBeenCalledOnce();
  },
);

it('局部横幅负责的请求保留后端原文，之后外层catch不重复提示', async () => {
  let failure: unknown;
  try {
    await authenticationClient.get('/captcha', {
      adapter: async (config) => ({
        config,
        data: body,
        status: 200,
        statusText: 'OK',
        headers: {},
      }),
    });
  } catch (error) {
    failure = error;
  }
  expect(stubs.message).not.toHaveBeenCalled();
  expect(takeErrorMessage(failure, '固定失败')).toBe('后端具体原因');
  notifyError(failure, '固定失败');
  expect(stubs.message).not.toHaveBeenCalled();
});

it.each([anonymousClient, requestClient])(
  'HTTP 403仍提取后端业务原文，不覆盖成通用HTTP文案',
  async (client) => {
    await expect(
      client.get('/failure', {
        adapter: async (config) => {
          throw new AxiosError(
            'Request failed with status code 403',
            'ERR_BAD_REQUEST',
            config,
            undefined,
            {
              config,
              data: body,
              status: 403,
              statusText: 'Forbidden',
              headers: {},
            },
          );
        },
      }),
    ).rejects.toMatchObject({ code: 1002002, message: '后端具体原因' });
    expect(stubs.message).toHaveBeenCalledExactlyOnceWith('后端具体原因');
  },
);

it('去重按错误实例，不吞掉下一次独立请求的相同业务错误', () => {
  const first = new BusinessError(body, {});
  const second = new BusinessError(body, {});
  notifyError(first);
  notifyError(first);
  notifyError(second);
  expect(stubs.message).toHaveBeenCalledTimes(2);
});

it('网络故障使用本地提示，取消与会话切换不产生失败消息', () => {
  const network = new AxiosError('Network Error', 'ERR_NETWORK');
  expect(getErrorMessage(network, '网络连接失败')).toBe('网络连接失败');
  notifyError(network, '网络连接失败');
  expect(stubs.message).toHaveBeenCalledExactlyOnceWith('网络连接失败');
  for (const error of [
    'cancel',
    'close',
    new DOMException('cancelled', 'AbortError'),
    new AxiosError('cancelled', 'ERR_CANCELED'),
    new SessionChangedError(),
  ]) {
    expect(takeErrorMessage(error, '失败')).toBe('');
  }
  expect(stubs.message).toHaveBeenCalledOnce();
});
