import { describe, expect, it, vi } from 'vitest';
import { RequestClient, authenticateResponseInterceptor } from '@vben/request';

import { BusinessError } from '../../dushan-admin-frontend/apps/web-ele/src/api/business-error';
import {
  configureNativeStreaming,
  isAuthenticationFailure,
  nativeResponseInterceptor,
  parseApiResponse,
} from '../../dushan-admin-frontend/apps/web-ele/src/api/response';

function envelope(code = 0, data: unknown = null) {
  return { code, data, message: code === 0 ? 'ok' : '登录已失效', error: null };
}

describe('业务响应与Vben请求接入', () => {
  it('真实请求拦截器按业务码解包，字段详情保留在业务异常上', async () => {
    const client = new RequestClient({ responseReturn: 'data' });
    client.addResponseInterceptor(nativeResponseInterceptor());
    const page = { items: [{ id: '1001' }], total: 1 };
    const adapter = vi.fn(async (config) => ({
      config,
      data: envelope(0, page),
      headers: {},
      status: 200,
      statusText: 'OK',
    }));
    expect(await client.get('/users', { adapter })).toEqual(page);
    const details = {
      fields: [{ field: 'mobile', message: '手机号格式不正确' }],
    };
    adapter.mockImplementation(async (config) => ({
      config,
      data: { ...envelope(422), error: details },
      headers: {},
      status: 200,
      statusText: 'OK',
    }));
    await expect(client.post('/users', {}, { adapter })).rejects.toMatchObject({
      code: 422,
      details,
      response: { status: 200 },
    });
  });

  it('登录过期按业务401刷新，并发请求只刷新一次后各自重试', async () => {
    const client = new RequestClient({ responseReturn: 'data' });
    client.addResponseInterceptor(nativeResponseInterceptor());
    const refresh = vi.fn(async () => {
      await Promise.resolve();
      return 'new-token';
    });
    const authenticate = vi.fn();
    client.addResponseInterceptor(
      authenticateResponseInterceptor({
        client,
        doReAuthenticate: authenticate,
        doRefreshToken: refresh,
        enableRefreshToken: true,
        formatToken: (token) => `Bearer ${token}`,
        isAuthError: isAuthenticationFailure,
      }),
    );
    const adapter = vi.fn(async (config) => ({
      config,
      data:
        config.headers.Authorization === 'Bearer new-token'
          ? envelope(0, config.url)
          : envelope(401),
      headers: {},
      status: 200,
      statusText: 'OK',
    }));
    expect(
      await Promise.all([
        client.get('/one', { adapter }),
        client.get('/two', { adapter }),
      ]),
    ).toEqual(['/one', '/two']);
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(authenticate).not.toHaveBeenCalled();
    expect(adapter).toHaveBeenCalledTimes(4);
  });

  it.each([
    '/system/auth/login',
    '/system/auth/refresh-token',
    '/system/auth/logout',
  ])('认证端点%s不会触发自身刷新', (url) => {
    const response = {
      config: { url },
      data: envelope(401),
      headers: {},
      status: 200,
      statusText: 'OK',
    };
    expect(
      isAuthenticationFailure(
        new BusinessError(response.data, response.config, response as never),
      ),
    ).toBe(false);
  });

  it('权限不足不刷新，HTTP传输故障也不伪造为业务登录失效', () => {
    const response = {
      config: { url: '/users' },
      data: envelope(403),
      headers: {},
      status: 200,
      statusText: 'OK',
    };
    expect(
      isAuthenticationFailure(
        new BusinessError(response.data, response.config, response as never),
      ),
    ).toBe(false);
    expect(isAuthenticationFailure({ response: { status: 401 } })).toBe(false);
  });

  it('业务端点即使路径含 auth 字样也按登录失效处理，排除名单只认后端真实端点名', () => {
    for (const url of [
      '/system/oauth2/token/page',
      '/system/auth-policy/list',
      '/system/user/auth/refresh-token-config',
      '/infra/auth/login',
      '/system/user/auth/logout',
      '/system/auth/login/records',
    ]) {
      const response = {
        config: { url },
        data: envelope(401),
        headers: {},
        status: 200,
        statusText: 'OK',
      };
      expect(
        isAuthenticationFailure(
          new BusinessError(response.data, response.config, response as never),
        ),
      ).toBe(true);
    }
  });

  it.each(
    [
      null,
      [],
      'html',
      { code: '0', message: 'ok', data: null, error: null },
      { code: 0, msg: 'ok', data: null },
      { code: 422, message: 'bad', data: null, error: 'duplicate' },
      {
        code: 422,
        message: 'bad',
        data: null,
        error: { fields: [{ field: 1, message: 'bad' }] },
      },
    ].map((body) => ({ body })),
  )('非法外部协议明确失败：$body', ({ body }) => {
    expect(() => parseApiResponse(body)).toThrow(/接口/);
  });

  it('文件body/raw模式保留原始内容和HTTP元数据', async () => {
    const client = new RequestClient({ responseReturn: 'data' });
    client.addResponseInterceptor(nativeResponseInterceptor());
    const adapter = async (config) => ({
      config,
      data: 'partial',
      headers: { 'content-range': 'bytes 1-3/6' },
      status: 206,
      statusText: 'Partial Content',
    });
    expect(await client.get('/file', { adapter, responseReturn: 'body' })).toBe(
      'partial',
    );
    expect(
      await client.get('/file', { adapter, responseReturn: 'raw' }),
    ).toMatchObject({ status: 206, data: 'partial' });
  });

  it('下载的200 JSON错误体进入业务失败，合法JSON附件仍是文件', async () => {
    const client = new RequestClient({ responseReturn: 'data' });
    client.addResponseInterceptor(nativeResponseInterceptor());
    const payload = new Blob([JSON.stringify(envelope(403))], {
      type: 'application/json',
    });
    const adapter = vi.fn(async (config) => ({
      config,
      data: payload,
      headers: { 'content-type': 'application/json' },
      status: 200,
      statusText: 'OK',
    }));
    await expect(client.download('/file', { adapter })).rejects.toMatchObject({
      code: 403,
    });
    adapter.mockImplementation(async (config) => ({
      config,
      data: payload,
      headers: {
        'content-type': 'application/json',
        'content-disposition': 'attachment; filename="data.json"',
      },
      status: 200,
      statusText: 'OK',
    }));
    expect(await client.download('/file', { adapter })).toBe(payload);
  });

  it('事件流的200 JSON错误不进入事件回调，POST数据按JSON发送', async () => {
    const client = new RequestClient({ baseURL: 'https://example.test/api' });
    configureNativeStreaming(client);
    const fetchMock = vi.fn(async () => Response.json(envelope(422)));
    vi.stubGlobal('fetch', fetchMock);
    const onMessage = vi.fn();
    try {
      await expect(
        client.postSSE('/events', { value: 1 }, { onMessage }),
      ).rejects.toMatchObject({ code: 422 });
      expect(onMessage).not.toHaveBeenCalled();
      expect(fetchMock.mock.calls[0]?.[1]?.body).toBe('{"value":1}');
      expect(fetchMock.mock.calls[0]?.[0]).toBe(
        'https://example.test/api/events',
      );
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('事件消费回调失败时取消流并释放reader，保留原始故障', async () => {
    const client = new RequestClient({ baseURL: 'https://example.test' });
    configureNativeStreaming(client);
    const cancel = vi.fn();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('data: test\n\n'));
      },
      cancel,
    });
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(stream, {
            headers: { 'content-type': 'text/event-stream' },
          }),
      ),
    );
    const original = new Error('consumer failed');
    try {
      await expect(
        client.requestSSE('/events', undefined, {
          onMessage() {
            throw original;
          },
        }),
      ).rejects.toBe(original);
      expect(cancel).toHaveBeenCalledOnce();
      expect(stream.locked).toBe(false);
    } finally {
      vi.unstubAllGlobals();
    }
  });
});
