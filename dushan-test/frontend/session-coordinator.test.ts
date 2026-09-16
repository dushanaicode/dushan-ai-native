import { describe, expect, it, vi } from 'vitest';

import {
  authenticateResponseInterceptor,
  AxiosError,
  RequestClient,
} from '@vben/request';

import {
  isAuthenticationFailure,
  nativeResponseInterceptor,
} from '../../dushan-admin-frontend/apps/web-ele/src/api/response';
import {
  SessionChangedError,
  SessionCoordinator,
  type SessionSnapshot,
} from '../../dushan-admin-frontend/apps/web-ele/src/services/session/coordinator';
import {
  configureSessionRequests,
  configureSessionStreaming,
} from '../../dushan-admin-frontend/apps/web-ele/src/services/session/http';

function createShared() {
  let snapshot: SessionSnapshot = { generation: 'first', token: 'old' };
  let queue = Promise.resolve();
  const listeners = new Set<() => void>();
  const refresh = vi.fn(async (_signal: AbortSignal) => 'new');
  const expire = vi.fn(async () => {});
  const create = () =>
    new SessionCoordinator({
      expire,
      lock(operation) {
        const result = queue.then(operation);
        queue = result.then(
          () => {},
          () => {},
        );
        return result;
      },
      read: () => snapshot,
      refresh,
      subscribe(listener) {
        listeners.add(listener);
        return () => {
          listeners.delete(listener);
        };
      },
      write(value) {
        snapshot = value;
      },
    });
  return { create, expire, listeners, refresh, read: () => snapshot };
}

function response(config: any, code: number, data: unknown = null) {
  return {
    config,
    data: { code, data, message: '结果', error: null },
    headers: {},
    status: 200,
    statusText: 'OK',
  };
}

describe('统一会话协调', () => {
  it('同代次共享刷新 Promise，两个标签页排锁后只调用一次 refresher', async () => {
    const shared = createShared();
    const first = shared.create();
    const second = shared.create();
    const pending = Promise.withResolvers<string>();
    shared.refresh.mockReturnValue(pending.promise);
    const scope = first.capture();
    const operation = first.refresh(scope);
    expect(first.refresh(scope)).toBe(operation);
    const other = second.refresh(second.capture());
    await vi.waitFor(() => expect(shared.refresh).toHaveBeenCalledTimes(1));
    pending.resolve('rotated');
    expect(await Promise.all([operation, other])).toEqual([
      'rotated',
      'rotated',
    ]);
    expect(shared.refresh).toHaveBeenCalledTimes(1);
    expect(second.capture().token).toBe('rotated');
  });

  it('刷新失败全部等待者收到同一错误，失效入口只调用一次', async () => {
    const shared = createShared();
    const session = shared.create();
    const pending = Promise.withResolvers<string>();
    shared.refresh.mockReturnValue(pending.promise);
    const scope = session.capture();
    const requests = Promise.allSettled([
      session.refresh(scope),
      session.refresh(scope),
    ]);
    const failure = new Error('刷新失败');
    pending.reject(failure);
    expect(await requests).toEqual([
      { status: 'rejected', reason: failure },
      { status: 'rejected', reason: failure },
    ]);
    expect(shared.expire).toHaveBeenCalledTimes(1);
    await Promise.all([session.expire(), session.expire()]);
    expect(shared.expire).toHaveBeenCalledTimes(1);
    expect(shared.read().token).toBeNull();
  });

  it('刷新中重新登录会取消旧刷新，忽略迟到成功且不让旧失败退出新会话', async () => {
    const shared = createShared();
    const session = shared.create();
    const pending = Promise.withResolvers<string>();
    shared.refresh.mockReturnValue(pending.promise);
    const operation = session.refresh();
    const result = Promise.allSettled([operation]);
    await vi.waitFor(() => expect(shared.refresh).toHaveBeenCalledTimes(1));
    const signal = shared.refresh.mock.calls[0]![0];
    session.replace('another-user');
    expect(signal.aborted).toBe(true);
    pending.resolve('obsolete');
    expect((await result)[0]).toMatchObject({
      status: 'rejected',
      reason: expect.any(SessionChangedError),
    });
    expect(shared.read().token).toBe('another-user');
    expect(shared.expire).not.toHaveBeenCalled();
  });

  it('安装可释放，dispose 后不响应跨标签事件或接受迟到刷新', async () => {
    const shared = createShared();
    const session = shared.create();
    session.install();
    session.install();
    expect(shared.listeners.size).toBe(1);
    const listener = vi.fn();
    session.subscribe(listener);
    shared.create().replace('external');
    for (const notify of shared.listeners) notify();
    expect(listener).toHaveBeenCalledTimes(1);
    const pending = Promise.withResolvers<string>();
    shared.refresh.mockReturnValue(pending.promise);
    const operation = Promise.allSettled([session.refresh()]);
    await vi.waitFor(() => expect(shared.refresh).toHaveBeenCalledTimes(1));
    session.dispose();
    expect(shared.listeners.size).toBe(0);
    pending.resolve('late');
    expect((await operation)[0]).toMatchObject({
      status: 'rejected',
      reason: expect.any(SessionChangedError),
    });
    expect(shared.read().token).toBe('external');
    expect(shared.expire).not.toHaveBeenCalled();
  });
});

describe('实际 Axios 请求与刷新边界', () => {
  it('旧会话下载错误体的迟到解析异常也被代次隔离', async () => {
    const shared = createShared();
    const session = shared.create();
    const client = new RequestClient({ responseReturn: 'data' });
    configureSessionRequests(
      client,
      () => session,
      () => true,
    );
    const pending = Promise.withResolvers<string>();
    const text = vi.fn(() => pending.promise);
    const adapter = async (config: any) => ({
      ...response(config, 0),
      data: { text },
      headers: { 'content-type': 'application/json' },
    });
    const request = Promise.allSettled([
      client.get('/download', { adapter, responseType: 'blob' }),
    ]);
    await vi.waitFor(() => expect(text).toHaveBeenCalledTimes(1));
    session.replace('another-user');
    pending.resolve('{invalid json');
    expect((await request)[0]).toMatchObject({
      status: 'rejected',
      reason: expect.any(SessionChangedError),
    });
  });

  it('流传输在返回 Promise 之前同步失败也会释放会话订阅', async () => {
    const session = createShared().create();
    const subscribe = session.subscribe.bind(session);
    const release = vi.fn();
    vi.spyOn(session, 'subscribe').mockImplementation((listener) => {
      const unsubscribe = subscribe(listener);
      return () => {
        release();
        return unsubscribe();
      };
    });
    const client = new RequestClient();
    const failure = new Error('invalid headers');
    client.requestSSE = () => {
      throw failure;
    };
    configureSessionStreaming(client, () => session);
    await expect(client.requestSSE('/events')).rejects.toBe(failure);
    expect(release).toHaveBeenCalledTimes(1);
    session.dispose();
  });

  it('切换会话或销毁都会取消流，迟到结束回调不能更新页面', async () => {
    for (const action of ['replace', 'dispose']) {
      const session = createShared().create();
      const client = new RequestClient();
      const pending = Promise.withResolvers<void>();
      const onEnd = vi.fn();
      let signal: AbortSignal | null | undefined;
      client.requestSSE = async (_url, _data, options) => {
        signal = options?.signal;
        await pending.promise;
        options?.onEnd?.();
      };
      configureSessionStreaming(client, () => session);
      const request = Promise.allSettled([
        client.requestSSE('/events', undefined, { onEnd }),
      ]);
      if (action === 'replace') session.replace('other');
      else session.dispose();
      expect(signal?.aborted).toBe(true);
      pending.resolve();
      expect((await request)[0]).toMatchObject({
        status: 'rejected',
        reason: expect.any(SessionChangedError),
      });
      expect(onEnd).not.toHaveBeenCalled();
      session.dispose();
    }
  });

  it('公共包刷新失败不会向等待队列发出空令牌重放', async () => {
    const client = new RequestClient({ responseReturn: 'data' });
    client.addResponseInterceptor(nativeResponseInterceptor());
    const pending = Promise.withResolvers<string>();
    const refresh = vi.fn(() => pending.promise);
    const expire = vi.fn(async () => {});
    client.addResponseInterceptor(
      authenticateResponseInterceptor({
        client,
        doRefreshToken: refresh,
        doReAuthenticate: expire,
        enableRefreshToken: true,
        formatToken: (token) => `Bearer ${token}`,
        isAuthError: isAuthenticationFailure,
      }),
    );
    const adapter = vi.fn(async (config) => response(config, 401));
    const requests = Promise.allSettled(
      ['/one', '/two', '/three'].map((url) => client.get(url, { adapter })),
    );
    await vi.waitFor(() => expect(adapter).toHaveBeenCalledTimes(3));
    const failure = new Error('refresh rejected');
    pending.reject(failure);
    const results = await requests;
    expect(
      results.every(
        (result) => result.status === 'rejected' && result.reason === failure,
      ),
    ).toBe(true);
    expect(adapter).toHaveBeenCalledTimes(3);
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(expire).toHaveBeenCalledTimes(1);
  });

  it('并发业务401只刷新一次，HTTP401同样支持，只用新令牌重放一次', async () => {
    const shared = createShared();
    const session = shared.create();
    const client = new RequestClient({ responseReturn: 'data' });
    configureSessionRequests(
      client,
      () => session,
      () => true,
    );
    const adapter = vi.fn(async (config) => {
      if (config.headers.Authorization === 'Bearer new')
        return response(config, 0, config.url);
      if (config.url === '/http')
        throw new AxiosError(
          'Unauthorized',
          'ERR_BAD_REQUEST',
          config,
          undefined,
          { ...response(config, 401), status: 401 },
        );
      return response(config, 401);
    });
    expect(
      await Promise.all(
        ['/one', '/http'].map((url) => client.get(url, { adapter })),
      ),
    ).toEqual(['/one', '/http']);
    expect(shared.refresh).toHaveBeenCalledTimes(1);
    expect(adapter).toHaveBeenCalledTimes(4);
  });

  it('再次401不循环；写请求须明确允许；认证端点不递归刷新', async () => {
    for (const [url, method, options, count, refreshes] of [
      ['/always', 'get', {}, 2, 1],
      ['/write', 'post', {}, 1, 1],
      ['/allowed', 'post', { allowAuthReplay: true }, 2, 1],
      ['/auth/refresh', 'get', {}, 1, 0],
      ['/auth/login', 'get', {}, 1, 0],
      ['/auth/logout', 'get', {}, 1, 0],
    ] as const) {
      const shared = createShared();
      const session = shared.create();
      const client = new RequestClient({ responseReturn: 'data' });
      configureSessionRequests(
        client,
        () => session,
        () => true,
      );
      const adapter = vi.fn(async (config) => response(config, 401));
      await expect(
        client.request(url, { method, adapter, ...options }),
      ).rejects.toMatchObject({ code: 401 });
      expect(adapter).toHaveBeenCalledTimes(count);
      expect(shared.refresh).toHaveBeenCalledTimes(refreshes);
    }
  });

  it('退出/切换代次后，迟到的成功响应不会交给调用方', async () => {
    const shared = createShared();
    const session = shared.create();
    const client = new RequestClient({ responseReturn: 'data' });
    configureSessionRequests(
      client,
      () => session,
      () => true,
    );
    const pending = Promise.withResolvers<void>();
    const adapter = vi.fn(async (config) => {
      await pending.promise;
      return response(config, 0, 'old-user');
    });
    const request = Promise.allSettled([client.get('/profile', { adapter })]);
    await vi.waitFor(() => expect(adapter).toHaveBeenCalledTimes(1));
    session.replace('another-user');
    pending.resolve();
    expect((await request)[0]).toMatchObject({
      status: 'rejected',
      reason: expect.any(SessionChangedError),
    });
  });
});
