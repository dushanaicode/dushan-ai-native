import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { readRealtimeConfig } from '../../dushan-admin-frontend/apps/web-ele/src/services/realtime';
import { SessionCoordinator } from '../../dushan-admin-frontend/apps/web-ele/src/services/session/coordinator';
import {
  buildSocketUrl,
  classifySocketClose,
  defaultSocketPolicy,
  SocketConnection,
} from '../../dushan-admin-frontend/apps/web-ele/src/services/websocket/connection';
import { socketProtocol } from '../../dushan-admin-frontend/apps/web-ele/src/services/websocket/protocol';

function at<T>(values: readonly T[], index: number): T {
  const value = values.at(index);
  if (value === undefined) throw new Error('测试未产生预期条目');
  return value;
}

class FakeSocket extends EventTarget {
  close = vi.fn();
  send = vi.fn();
  end(code: number) {
    this.dispatchEvent(new CloseEvent('close', { code }));
  }
  open() {
    this.dispatchEvent(new Event('open'));
  }
  receive(type: string) {
    this.dispatchEvent(
      new MessageEvent('message', {
        data: JSON.stringify({ type, timestamp: Date.now() }),
      }),
    );
  }
}

const cleanup: Array<() => void> = [];
beforeEach(() => {
  vi.useFakeTimers();
  vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(true);
  vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible');
});
afterEach(() => {
  for (const dispose of cleanup.splice(0)) dispose();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

function fixture(random = 0.5) {
  let snapshot = { generation: 'first', token: 'old' as null | string };
  const refresh = vi.fn(async (_signal: AbortSignal) => 'new');
  const session = new SessionCoordinator({
    read: () => snapshot,
    write: (value) => {
      snapshot = { ...value };
    },
    refresh,
    expire: async () => {},
    lock: (operation) => operation(),
    subscribe: () => () => {},
  });
  const sockets: FakeSocket[] = [];
  const getTicket = vi.fn(async (_signal: AbortSignal) => ({
    ticket: 'single-use',
    expiresAtMs: Date.now() + 10_000,
  }));
  const errors: unknown[] = [];
  const connection = new SocketConnection({
    session,
    getTicket,
    protocol: socketProtocol,
    baseUrl: new URL('wss://example.com/api/live'),
    buildUrl: (base, ticket) => buildSocketUrl(base, ticket, 'test'),
    classifyClose: classifySocketClose,
    policy: {
      ...defaultSocketPolicy,
      heartbeatIntervalMs: 100,
      heartbeatTimeoutMs: 30,
      connectTimeoutMs: 200,
      retryBaseMs: 10,
      retryMaxMs: 50,
      maxRetries: 3,
      authRetryDelayMs: 5,
    },
    createSocket: () => {
      const socket = new FakeSocket();
      sockets.push(socket);
      return socket as unknown as WebSocket;
    },
    random: () => random,
    onError: (error) => errors.push(error),
  });
  cleanup.push(() => {
    connection.dispose();
    session.dispose();
  });
  return { connection, session, getTicket, sockets, refresh, errors };
}

describe('websocket 生命周期与并发', () => {
  it('心跳有响应则保活，超时按退避重连', async () => {
    const { connection, sockets, errors } = fixture();
    await connection.connect();
    at(sockets, 0).open();
    await vi.advanceTimersByTimeAsync(100);
    expect(JSON.parse(at(at(sockets, 0).send.mock.calls, 0)[0])).toEqual({
      type: 'ping',
    });
    at(sockets, 0).receive('pong');
    await vi.advanceTimersByTimeAsync(0);
    await vi.advanceTimersByTimeAsync(30);
    expect(at(sockets, 0).close).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(100);
    expect(connection.status).toBe('backoff');
    expect(errors).toHaveLength(1);
    await vi.advanceTimersByTimeAsync(10);
    expect(sockets).toHaveLength(2);
  });

  it('连接数限制也有界重试，10/20/40 退避后停止，网络事件允许恢复', async () => {
    const { connection, sockets } = fixture();
    await connection.connect();
    for (const delay of [10, 20, 40]) {
      at(sockets, -1).end(4003);
      await vi.advanceTimersByTimeAsync(0);
      const count = sockets.length;
      await vi.advanceTimersByTimeAsync(delay - 1);
      expect(sockets).toHaveLength(count);
      await vi.advanceTimersByTimeAsync(1);
      expect(sockets).toHaveLength(count + 1);
    }
    at(sockets, -1).end(4003);
    await vi.advanceTimersByTimeAsync(0);
    expect(connection.status).toBe('exhausted');
    await vi.advanceTimersByTimeAsync(1000);
    expect(sockets).toHaveLength(4);
    window.dispatchEvent(new Event('online'));
    await vi.advanceTimersByTimeAsync(0);
    expect(sockets).toHaveLength(5);
  });

  it('抖动在 0.75 到 1.25 倍内，建连也有超时', async () => {
    for (const [random, delay] of [
      [0, 7],
      [0.999999, 12],
    ]) {
      const { connection, sockets } = fixture(random);
      await connection.connect();
      await vi.advanceTimersByTimeAsync(200);
      expect(connection.status).toBe('backoff');
      await vi.advanceTimersByTimeAsync(delay - 1);
      expect(sockets).toHaveLength(1);
      await vi.advanceTimersByTimeAsync(1);
      expect(sockets).toHaveLength(2);
      connection.dispose();
    }
  });

  it('一个业务处理器失败不会阻止其他处理器，协议错误触发有界恢复', async () => {
    const { connection, sockets, errors } = fixture();
    const next = vi.fn();
    connection.on('event', () => {
      throw new Error('handler');
    });
    connection.on('event', next);
    await connection.connect();
    at(sockets, 0).open();
    at(sockets, 0).receive('event');
    await vi.advanceTimersByTimeAsync(0);
    expect(next).toHaveBeenCalledOnce();
    expect(errors[0]).toBeInstanceOf(AggregateError);
    at(sockets, 0).dispatchEvent(new MessageEvent('message', { data: '{bad' }));
    await vi.advanceTimersByTimeAsync(0);
    expect(connection.status).toBe('backoff');
  });

  it('取票期间断开取消信号，迟到票据不创建连接', async () => {
    const { connection, getTicket, sockets } = fixture();
    const pending = Promise.withResolvers<{
      ticket: string;
      expiresAtMs: number;
    }>();
    getTicket.mockReturnValue(pending.promise);
    const result = Promise.allSettled([connection.connect()]);
    await vi.advanceTimersByTimeAsync(0);
    const signal = at(getTicket.mock.calls, 0)[0];
    connection.disconnect();
    expect(signal.aborted).toBe(true);
    pending.resolve({ ticket: 'late', expiresAtMs: Date.now() + 1000 });
    const completed = await result;
    expect(at(completed, 0)).toMatchObject({
      status: 'rejected',
      reason: expect.any(DOMException),
    });
    expect(sockets).toHaveLength(0);
  });

  it('认证关闭与 HTTP 侧并发恢复共用一个刷新，成功后重新取票', async () => {
    const { connection, session, sockets, refresh } = fixture();
    await connection.connect();
    at(sockets, 0).open();
    const pending = Promise.withResolvers<string>();
    refresh.mockReturnValue(pending.promise);
    const http = session.refresh();
    at(sockets, 0).end(4001);
    await vi.advanceTimersByTimeAsync(0);
    expect(refresh).toHaveBeenCalledOnce();
    pending.resolve('new-token');
    await http;
    await vi.advanceTimersByTimeAsync(5);
    expect(sockets).toHaveLength(2);
  });

  it('旧消息与已经排队的 open 回调在销毁后无效，浏览器事件不再激活', async () => {
    const { connection, sockets, session, getTicket } = fixture();
    const message = vi.fn();
    const connected = vi.fn();
    connection.on('event', message);
    connection.onConnected(connected);
    await connection.connect();
    at(sockets, 0).open();
    connection.dispose();
    at(sockets, 0).receive('event');
    window.dispatchEvent(new Event('online'));
    document.dispatchEvent(new Event('visibilitychange'));
    session.replace('other');
    await vi.advanceTimersByTimeAsync(1000);
    expect(connected).not.toHaveBeenCalled();
    expect(message).not.toHaveBeenCalled();
    expect(getTicket).toHaveBeenCalledOnce();
    expect(connection.status).toBe('disposed');
  });
});

describe('实时协议与配置', () => {
  it('信封拒绝未知键、无时间戳、数值 ID 和非 JSON，错误不反射内容', () => {
    for (const frame of [
      { type: 'event' },
      { type: 'event', timestamp: 0, extra: 1 },
      { type: 'event', timestamp: 0, senderId: 1 },
      { type: 'status_change', timestamp: 0 },
      { type: 'Event', timestamp: 0 },
      { type: 'event', timestamp: 0.5 },
    ])
      expect(() => socketProtocol.parse(JSON.stringify(frame))).toThrow(
        /WebSocket/,
      );
    expect(() => socketProtocol.parse('secret-data')).toThrow('不是有效 JSON');
    expect(
      socketProtocol.parse(
        '{"type":"event","timestamp":0,"senderId":"9223372036854775807"}',
      ).senderId,
    ).toBe('9223372036854775807');
  });
  it('握手参数与关闭码遵循服务端契约', () => {
    const url = buildSocketUrl(
      new URL('wss://example.com/api/ws'),
      { ticket: 'one-use-ticket', expiresAtMs: Date.now() + 1000 },
      'management',
    );
    expect([...url.searchParams.keys()]).toEqual(['ticket', 'audience']);
    expect(classifySocketClose(4001)).toBe('auth');
    expect(classifySocketClose(1013)).toBe('limited');
    expect(classifySocketClose(4002)).toBe('stop');
    expect(classifySocketClose(1001)).toBe('retry');
  });
  it('未启用不需要地址，启用只能同源 /api', () => {
    expect(
      readRealtimeConfig({ enabled: 'false', path: '' }, 'https://example.com'),
    ).toEqual({ enabled: false });
    expect(
      readRealtimeConfig(
        { enabled: 'true', path: '/api/live' },
        'https://example.com',
      ),
    ).toMatchObject({
      enabled: true,
      url: new URL('wss://example.com/api/live'),
    });
    for (const path of [
      '/live',
      'https://other.example/api/live',
      '/api/live?ticket=secret',
    ])
      expect(() =>
        readRealtimeConfig({ enabled: 'true', path }, 'https://example.com'),
      ).toThrow(/VITE_WEBSOCKET_PATH/);
  });
});
