import type {
  SessionCoordinator,
  SessionSnapshot,
} from '../session/coordinator';
import type { SocketCommand, SocketMessage, SocketProtocol } from './protocol';

import { shallowRef } from 'vue';

import { SessionChangedError } from '../session/coordinator';

export interface SocketTicket {
  ticket: string;
  expiresAtMs: number;
}
export interface SocketPolicy {
  heartbeatIntervalMs: number;
  heartbeatTimeoutMs: number;
  connectTimeoutMs: number;
  retryBaseMs: number;
  retryMaxMs: number;
  maxRetries: number;
  maxAuthRetries: number;
  authRetryDelayMs: number;
}
export const defaultSocketPolicy: SocketPolicy = {
  heartbeatIntervalMs: 30_000,
  heartbeatTimeoutMs: 15_000,
  connectTimeoutMs: 10_000,
  retryBaseMs: 3000,
  retryMaxMs: 60_000,
  maxRetries: 5,
  maxAuthRetries: 3,
  authRetryDelayMs: 500,
};
type SocketState =
  | 'backoff'
  | 'closed'
  | 'connecting'
  | 'disposed'
  | 'exhausted'
  | 'idle'
  | 'open'
  | 'recovering'
  | 'ticket';
type Handler = (message: SocketMessage) => unknown;

export class SocketConnection {
  get error() {
    return this.lastError.value;
  }
  get retryCount() {
    return this.retries;
  }
  get status() {
    return this.state.value;
  }
  private authRetries = 0;
  private connected = new Set<() => Promise<void> | void>();
  private deadline: ReturnType<typeof setTimeout> | undefined;
  private disposed = false;
  private generation = 0;
  private handlers = new Map<string, Set<Handler>>();
  private handshake: ReturnType<typeof setTimeout> | undefined;
  private heartbeat: ReturnType<typeof setInterval> | undefined;
  private lastError = shallowRef<unknown>();
  private opening: Promise<void> | undefined;
  private retries = 0;
  private retry: ReturnType<typeof setTimeout> | undefined;
  private socket: undefined | WebSocket;
  private state = shallowRef<SocketState>('idle');

  private ticketController: AbortController | undefined;

  private unsubscribe: () => void;
  private wanted = false;
  constructor(
    private readonly options: {
      baseUrl: URL;
      buildUrl: (base: URL, ticket: SocketTicket) => URL;
      classifyClose: (code: number) => 'auth' | 'limited' | 'retry' | 'stop';
      getTicket: (signal: AbortSignal) => Promise<SocketTicket>;
      onError: (error: unknown) => void;
      policy: SocketPolicy;
      protocol: SocketProtocol;
      session: SessionCoordinator;
      createSocket?: (url: string) => WebSocket;
      random?: () => number;
    },
  ) {
    this.unsubscribe = options.session.subscribe((next, previous) => {
      if (next.generation !== previous.generation) {
        this.teardown();
        this.retries = 0;
        this.authRetries = 0;
        this.state.value = 'idle';
        if (this.wanted) this.background(() => this.start());
      } else if (
        next.token !== previous.token &&
        ['backoff', 'exhausted', 'idle'].includes(this.status)
      )
        this.resume();
    });
    window.addEventListener('online', this.onOnline);
    window.addEventListener('offline', this.onOffline);
    document.addEventListener('visibilitychange', this.onVisibility);
    options.session.signal.addEventListener('abort', this.onDispose, {
      once: true,
    });
  }

  connect(): Promise<void> {
    if (this.disposed) return Promise.reject(new Error('WebSocket 实例已关闭'));
    this.wanted = true;
    if (this.socket || this.opening) return this.opening ?? Promise.resolve();
    this.retries = 0;
    this.authRetries = 0;
    this.state.value = 'idle';
    clearTimeout(this.retry);
    return this.start();
  }

  disconnect() {
    this.wanted = false;
    this.teardown();
    this.state.value = 'idle';
  }

  dispose() {
    if (this.disposed) return;
    this.disconnect();
    this.disposed = true;
    this.state.value = 'disposed';
    this.unsubscribe();
    window.removeEventListener('online', this.onOnline);
    window.removeEventListener('offline', this.onOffline);
    document.removeEventListener('visibilitychange', this.onVisibility);
    this.options.session.signal.removeEventListener('abort', this.onDispose);
    this.handlers.clear();
    this.connected.clear();
  }

  on(type: string, handler: Handler) {
    let group = this.handlers.get(type);
    if (!group) {
      group = new Set();
      this.handlers.set(type, group);
    }
    const handlers = group;
    handlers.add(handler);
    return () => {
      handlers.delete(handler);
      if (handlers.size === 0 && this.handlers.get(type) === handlers)
        this.handlers.delete(type);
    };
  }

  onConnected(handler: () => Promise<void> | void) {
    this.connected.add(handler);
    return () => this.connected.delete(handler);
  }

  send(command: SocketCommand) {
    if (this.status !== 'open' || !this.socket)
      throw new Error('WebSocket 尚未连接');
    this.socket.send(this.options.protocol.encode(command));
  }

  private allowed() {
    return (
      this.wanted &&
      !this.disposed &&
      navigator.onLine &&
      document.visibilityState === 'visible' &&
      this.options.session.capture().token !== null
    );
  }

  private background(operation: () => unknown) {
    void Promise.resolve()
      .then(operation)
      .catch((error) => this.report(error));
  }

  private async closed(
    code: number,
    generation: number,
    scope: SessionSnapshot,
  ) {
    if (!this.current(generation, scope)) return;
    this.teardown();
    const policy = this.options.classifyClose(code);
    if (policy === 'stop') {
      this.state.value = 'closed';
      return;
    }
    if (policy !== 'auth') {
      this.schedule();
      return;
    }
    if (this.authRetries >= this.options.policy.maxAuthRetries) {
      this.state.value = 'exhausted';
      return;
    }
    this.authRetries += 1;
    this.state.value = 'recovering';
    const recovery = this.generation;
    try {
      await this.options.session.refresh(scope);
    } catch (error) {
      if (recovery === this.generation) this.state.value = 'exhausted';
      throw error;
    }
    if (!this.current(recovery, scope)) return;
    this.retry = setTimeout(
      () => this.background(() => this.start()),
      this.options.policy.authRetryDelayMs,
    );
  }

  private current(generation: number, scope: SessionSnapshot) {
    return (
      !this.disposed &&
      this.wanted &&
      generation === this.generation &&
      this.options.session.capture().generation === scope.generation
    );
  }

  private async message(
    data: unknown,
    generation: number,
    scope: SessionSnapshot,
  ) {
    if (!this.current(generation, scope)) return;
    let message: SocketMessage;
    try {
      message = this.options.protocol.parse(data);
    } catch (error) {
      this.teardown();
      this.schedule();
      throw error;
    }
    clearTimeout(this.deadline);
    this.deadline = undefined;
    this.retries = 0;
    this.authRetries = 0;
    if (message.type === 'ping') {
      this.send({ type: 'pong' });
      return;
    }
    if (message.type === 'pong') return;
    const handlers = [...(this.handlers.get(message.type) ?? [])];
    const results = await Promise.allSettled(
      handlers.map((handler) =>
        Promise.resolve().then(() => {
          if (this.current(generation, scope)) return handler(message);
        }),
      ),
    );
    if (!this.current(generation, scope)) return;
    const errors = results
      .filter((result) => result.status === 'rejected')
      .map((result) => result.reason);
    if (errors.length > 0)
      throw new AggregateError(errors, 'WebSocket 消息处理失败');
  }

  private onDispose = () => this.dispose();

  private onOffline = () => {
    this.teardown();
    this.state.value = 'idle';
  };

  private onOnline = () => this.resume();

  private onVisibility = () => {
    if (document.visibilityState === 'visible') this.resume();
    else this.onOffline();
  };
  private report(error: unknown) {
    if (this.disposed || this.lastError.value === error) return;
    if (
      error instanceof SessionChangedError ||
      (error instanceof DOMException && error.name === 'AbortError')
    )
      return;
    this.lastError.value = error;
    this.options.onError(error);
  }
  private resume() {
    if (
      !this.wanted ||
      this.disposed ||
      this.status === 'closed' ||
      this.socket ||
      this.opening
    )
      return;
    this.retries = 0;
    this.authRetries = 0;
    this.background(() => this.start());
  }
  private schedule() {
    if (!this.allowed()) {
      this.state.value = 'idle';
      return;
    }
    if (this.retries >= this.options.policy.maxRetries) {
      this.state.value = 'exhausted';
      return;
    }
    this.retries += 1;
    const jitter = 0.75 + (this.options.random ?? Math.random)() * 0.5;
    const delay = Math.min(
      this.options.policy.retryBaseMs * 2 ** (this.retries - 1) * jitter,
      this.options.policy.retryMaxMs,
    );
    this.state.value = 'backoff';
    this.retry = setTimeout(() => this.background(() => this.start()), delay);
  }
  private start(): Promise<void> {
    if (!this.allowed()) return Promise.resolve();
    if (this.opening) return this.opening;
    this.teardown();
    const generation = this.generation;
    const scope = this.options.session.capture();
    const controller = new AbortController();
    this.ticketController = controller;
    this.state.value = 'ticket';
    const opening = Promise.resolve()
      .then(() => {
        controller.signal.throwIfAborted();
        return this.options.getTicket(controller.signal);
      })
      .then((ticket) => {
        if (!this.current(generation, scope)) throw new SessionChangedError();
        controller.signal.throwIfAborted();
        if (
          typeof ticket.ticket !== 'string' ||
          !ticket.ticket ||
          !Number.isSafeInteger(ticket.expiresAtMs) ||
          ticket.expiresAtMs <= Date.now()
        )
          throw new TypeError('WebSocket 票据无效或已过期');
        const url = this.options.buildUrl(
          new URL(this.options.baseUrl),
          ticket,
        );
        if (
          url.origin !== this.options.baseUrl.origin ||
          !url.pathname.startsWith('/api/') ||
          url.username ||
          url.password ||
          url.hash
        )
          throw new TypeError('WebSocket 地址必须位于同源 /api 下');
        const socket = (
          this.options.createSocket ?? ((address) => new WebSocket(address))
        )(url.href);
        this.socket = socket;
        this.state.value = 'connecting';
        socket.addEventListener(
          'open',
          () => {
            if (!this.current(generation, scope)) return;
            clearTimeout(this.handshake);
            this.state.value = 'open';
            this.lastError.value = undefined;
            this.startHeartbeat(generation, scope);
            for (const handler of [...this.connected])
              this.background(() => {
                if (this.current(generation, scope)) return handler();
              });
          },
          { signal: controller.signal },
        );
        socket.addEventListener(
          'message',
          (event) =>
            this.background(() => this.message(event.data, generation, scope)),
          { signal: controller.signal },
        );
        socket.addEventListener(
          'error',
          () => {
            if (this.current(generation, scope))
              this.report(new Error('WebSocket 传输错误'));
          },
          { signal: controller.signal },
        );
        socket.addEventListener(
          'close',
          (event) =>
            this.background(() => this.closed(event.code, generation, scope)),
          { signal: controller.signal },
        );
        this.handshake = setTimeout(() => {
          if (!this.current(generation, scope)) return;
          this.teardown();
          this.schedule();
          this.report(new Error('WebSocket 建连超时'));
        }, this.options.policy.connectTimeoutMs);
      })
      .catch((error: unknown) => {
        if (!this.current(generation, scope))
          throw new DOMException('连接尝试已取消', 'AbortError');
        this.teardown();
        this.schedule();
        throw error;
      })
      .finally(() => {
        if (this.opening === opening) this.opening = undefined;
      });
    this.opening = opening;
    return opening;
  }
  private startHeartbeat(generation: number, scope: SessionSnapshot) {
    this.heartbeat = setInterval(
      () =>
        this.background(() => {
          if (!this.current(generation, scope) || this.deadline !== undefined)
            return;
          this.send({ type: 'ping' });
          this.deadline = setTimeout(() => {
            if (!this.current(generation, scope)) return;
            this.teardown();
            this.schedule();
            this.report(new Error('WebSocket 心跳超时'));
          }, this.options.policy.heartbeatTimeoutMs);
        }),
      this.options.policy.heartbeatIntervalMs,
    );
  }
  private teardown() {
    this.generation += 1;
    this.ticketController?.abort();
    this.ticketController = undefined;
    this.opening = undefined;
    clearInterval(this.heartbeat);
    clearTimeout(this.deadline);
    clearTimeout(this.handshake);
    clearTimeout(this.retry);
    this.heartbeat = undefined;
    this.deadline = undefined;
    this.handshake = undefined;
    this.retry = undefined;
    if (this.socket) {
      this.socket.close(1000);
      this.socket = undefined;
    }
  }
}
