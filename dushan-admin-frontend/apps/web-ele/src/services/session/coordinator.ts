export interface SessionSnapshot {
  readonly generation: string;
  readonly token: null | string;
}

export interface SessionPorts {
  expire: () => Promise<void>;
  lock: (operation: () => Promise<string>) => Promise<string>;
  read: () => SessionSnapshot;
  refresh: (signal: AbortSignal) => Promise<string>;
  subscribe: (listener: () => void) => () => void;
  write: (snapshot: SessionSnapshot) => void;
}

export class SessionChangedError extends Error {
  constructor() {
    super('登录会话已经变化，本次结果不再有效');
    this.name = 'SessionChangedError';
  }
}

export class SessionCoordinator {
  get signal() {
    return this.lifetime.signal;
  }
  private disposed = false;
  private expiration: Promise<void> | undefined;
  private lifetime = new AbortController();
  private listeners = new Set<
    (
      next: SessionSnapshot,
      previous: SessionSnapshot,
      source: 'external' | 'local',
    ) => void
  >();
  private pending:
    | undefined
    | {
        controller: AbortController;
        generation: string;
        promise: Promise<string>;
      };
  private snapshot: SessionSnapshot;

  private unsubscribe: (() => void) | undefined;

  constructor(private readonly ports: SessionPorts) {
    this.snapshot = ports.read();
  }

  assertCurrent(expected: SessionSnapshot) {
    const current = this.capture();
    if (current.generation !== expected.generation)
      throw new SessionChangedError();
    return current;
  }

  capture(): SessionSnapshot {
    this.assertActive();
    this.adopt(this.ports.read(), 'external');
    return this.snapshot;
  }

  dispose() {
    this.disposed = true;
    this.lifetime.abort();
    this.pending?.controller.abort();
    this.unsubscribe?.();
    this.unsubscribe = undefined;
    this.listeners.clear();
  }

  expire(expected = this.capture()): Promise<void> {
    if (this.expiration) return this.expiration;
    if (this.capture().generation !== expected.generation)
      return Promise.resolve();
    this.replace(null);
    this.expiration = Promise.resolve().then(() => this.ports.expire());
    return this.expiration;
  }

  install() {
    this.assertActive();
    this.unsubscribe ??= this.ports.subscribe(() => this.capture());
  }

  refresh(expected = this.capture()): Promise<string> {
    this.assertCurrent(expected);
    const current = this.snapshot;
    if (current.token === null)
      return Promise.reject(new SessionChangedError());
    if (current.token !== expected.token) return Promise.resolve(current.token);
    if (this.pending?.generation === expected.generation)
      return this.pending.promise;

    const controller = new AbortController();
    const promise = this.ports
      .lock(async () => {
        this.assertCurrent(expected);
        // 拿到跨标签页锁后重读持久状态，复用其他标签页刚刷新的令牌。
        if (this.snapshot.token !== expected.token)
          return this.snapshot.token as string;
        const token = await this.ports.refresh(controller.signal);
        this.assertCurrent(expected);
        const next = { generation: expected.generation, token };
        this.ports.write(next);
        this.adopt(next, 'local');
        return token;
      })
      .catch(async (error: unknown) => {
        if (
          !this.disposed &&
          this.capture().generation === expected.generation
        ) {
          await this.expire(expected);
        }
        throw error;
      })
      .finally(() => {
        if (this.pending?.promise === promise) this.pending = undefined;
      });
    this.pending = { controller, generation: expected.generation, promise };
    return promise;
  }

  replace(token: null | string) {
    this.assertActive();
    this.expiration = undefined;
    const next = { generation: crypto.randomUUID(), token };
    this.ports.write(next);
    this.adopt(next, 'local');
  }

  subscribe(
    listener: (
      next: SessionSnapshot,
      previous: SessionSnapshot,
      source: 'external' | 'local',
    ) => void,
  ) {
    this.assertActive();
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private adopt(next: SessionSnapshot, source: 'external' | 'local') {
    const previous = this.snapshot;
    if (
      next.generation === previous.generation &&
      next.token === previous.token
    )
      return;
    if (next.generation !== previous.generation) {
      this.pending?.controller.abort();
      this.expiration = undefined;
    }
    this.snapshot = next;
    for (const listener of this.listeners) listener(next, previous, source);
  }

  private assertActive() {
    if (this.disposed) throw new SessionChangedError();
  }
}
