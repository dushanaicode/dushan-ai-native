import type { WatchStopHandle } from 'vue';

import type { SessionCoordinator } from '../session/coordinator';
import type { SocketMessage } from '../websocket/protocol';

import { shallowRef, watch } from 'vue';

import { z } from '@vben/common-ui';

const notificationSchema = z
  .object({
    id: z.string().min(1),
    title: z.string(),
    content: z.string(),
    createTime: z.string(),
    isRead: z.boolean(),
  })
  .strict();
const recentSchema = z
  .object({
    items: z.array(notificationSchema),
    total: z.number().int().nonnegative(),
  })
  .strict();
const countSchema = z.number().int().nonnegative();
const dedupSchema = z
  .object({ generation: z.string(), ids: z.array(z.string().min(1)).max(512) })
  .strict();
export type NotificationRecord = Readonly<z.infer<typeof notificationSchema>>;
export interface NotificationPorts {
  list: (signal: AbortSignal) => Promise<unknown>;
  unread: (signal: AbortSignal) => Promise<unknown>;
  read: (id: string, signal: AbortSignal) => Promise<void>;
  readAll: (signal: AbortSignal) => Promise<void>;
  notify: (notification: NotificationRecord) => void;
  onError: (error: unknown) => void;
}

export class NotificationRuntime {
  get error() {
    return this.state.value.error;
  }
  get loading() {
    return this.state.value.loading;
  }
  get needRefresh() {
    return this.state.value.needRefresh;
  }
  get notifications() {
    return [...this.state.value.items.values()].slice(
      0,
      this.options.recentLimit,
    );
  }
  get unreadCount() {
    return this.state.value.unreadCount;
  }
  private allRead: Promise<void> | undefined;
  private controller = new AbortController();
  private countPending: Promise<void> | undefined;
  private disposed = false;
  private epoch = 0;
  private listPending: Promise<void> | undefined;
  private polling: ReturnType<typeof setInterval> | undefined;
  private reads = new Map<string, Promise<void>>();
  private revision = 0;

  private seen = new Set<string>();

  private state = shallowRef({
    items: new Map<string, NotificationRecord>(),
    unreadCount: 0,
    needRefresh: true,
    loading: false,
    error: undefined as unknown,
  });
  private stopSession: () => void;
  private subscriptions = new Set<WatchStopHandle>();
  private updated = new Map<string, number>();
  constructor(
    private readonly options: {
      session: SessionCoordinator;
      ports: NotificationPorts;
      storage: Storage;
      storageKey: string;
      recentLimit: number;
      pollIntervalMs: number;
    },
  ) {
    this.restoreSeen();
    this.stopSession = options.session.subscribe((next, previous) => {
      if (next.generation !== previous.generation) this.clear();
      this.syncPolling();
    });
    window.addEventListener('online', this.onAvailability);
    window.addEventListener('offline', this.onAvailability);
    document.addEventListener('visibilitychange', this.onAvailability);
    options.session.signal.addEventListener('abort', this.onDispose, {
      once: true,
    });
    this.syncPolling();
  }

  addNotification(notification: NotificationRecord) {
    this.assertActive();
    if (this.state.value.items.has(notification.id)) return false;
    this.revision += 1;
    this.updated.set(notification.id, this.revision);
    this.patch({
      items: new Map([
        [notification.id, notification],
        ...this.state.value.items,
      ]),
      unreadCount: this.unreadCount + (notification.isRead ? 0 : 1),
      needRefresh: true,
    });
    return true;
  }

  clear() {
    this.controller.abort();
    this.controller = new AbortController();
    this.epoch += 1;
    this.listPending = undefined;
    this.countPending = undefined;
    this.reads.clear();
    this.allRead = undefined;
    this.updated.clear();
    this.seen.clear();
    this.revision = 0;
    this.patch({
      items: new Map(),
      unreadCount: 0,
      needRefresh: true,
      loading: false,
      error: undefined,
    });
    this.persistSeen();
  }

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    this.controller.abort();
    clearInterval(this.polling);
    this.stopSession();
    window.removeEventListener('online', this.onAvailability);
    window.removeEventListener('offline', this.onAvailability);
    document.removeEventListener('visibilitychange', this.onAvailability);
    this.options.session.signal.removeEventListener('abort', this.onDispose);
    for (const stop of this.subscriptions) stop();
    this.subscriptions.clear();
    this.listPending = undefined;
    this.countPending = undefined;
    this.reads.clear();
    this.allRead = undefined;
    this.patch({
      items: new Map(),
      unreadCount: 0,
      needRefresh: true,
      loading: false,
    });
  }

  ensure() {
    this.assertActive();
    this.options.session.capture();
    return this.needRefresh ? this.refresh() : Promise.resolve();
  }

  handle(message: SocketMessage) {
    this.assertActive();
    this.options.session.capture();
    if (message.requestId === undefined)
      throw new TypeError('通知消息缺少 requestId');
    if (this.seen.has(message.requestId)) return false;
    const notification = Object.freeze(
      notificationSchema.parse(message.payload),
    );
    const added = this.addNotification(notification);
    this.remember(message.requestId);
    if (added) {
      try {
        this.options.ports.notify(notification);
      } finally {
        this.requestCount();
      }
    }
    return added;
  }

  markAllRead(): Promise<void> {
    this.assertActive();
    const scope = this.options.session.capture();
    const epoch = this.epoch;
    if (this.allRead) return this.allRead;
    const ids = [...this.state.value.items.keys()];
    const pending = this.options.ports
      .readAll(this.controller.signal)
      .then(() => {
        this.assertCurrent(epoch, scope.generation);
        const items = new Map(this.state.value.items);
        for (const id of ids) {
          const item = items.get(id);
          if (item) {
            items.set(id, Object.freeze({ ...item, isRead: true }));
            this.updated.set(id, ++this.revision);
          }
        }
        this.patch({
          items,
          unreadCount: [...items.values()].filter((item) => !item.isRead)
            .length,
        });
        this.requestCount();
      })
      .finally(() => {
        if (this.allRead === pending) this.allRead = undefined;
      });
    this.allRead = pending;
    return pending;
  }

  markRead(id: string): Promise<void> {
    this.assertActive();
    const scope = this.options.session.capture();
    const epoch = this.epoch;
    if (this.state.value.items.get(id)?.isRead) return Promise.resolve();
    const existing = this.reads.get(id);
    if (existing) return existing;
    const pending = this.options.ports
      .read(id, this.controller.signal)
      .then(() => {
        this.assertCurrent(epoch, scope.generation);
        const item = this.state.value.items.get(id);
        if (item && !item.isRead) {
          const items = new Map(this.state.value.items);
          items.set(id, Object.freeze({ ...item, isRead: true }));
          this.updated.set(id, ++this.revision);
          this.patch({ items, unreadCount: Math.max(0, this.unreadCount - 1) });
        }
        this.requestCount();
      })
      .finally(() => {
        if (this.reads.get(id) === pending) this.reads.delete(id);
      });
    this.reads.set(id, pending);
    return pending;
  }

  refresh(): Promise<void> {
    this.assertActive();
    const scope = this.options.session.capture();
    const epoch = this.epoch;
    if (this.listPending) return this.listPending;
    const revision = this.revision;
    this.patch({ loading: true, error: undefined });
    const pending = this.options.ports
      .list(this.controller.signal)
      .then(async (value) => {
        this.assertCurrent(epoch, scope.generation);
        const { items } = recentSchema.parse(value);
        const current = this.state.value.items;
        const fetched = items.map(
          (item) =>
            [
              item.id,
              Object.freeze({
                ...item,
                isRead: item.isRead || current.get(item.id)?.isRead === true,
              }),
            ] as const,
        );
        const pushed = [...current].filter(
          ([id]) => (this.updated.get(id) ?? 0) > revision,
        );
        // ponytail: 会话内保留已见记录用于 ID 去重；高吞吐时改用服务端游标窗口。
        const merged = new Map([...pushed, ...fetched]);
        for (const [id, item] of current)
          if (!merged.has(id)) merged.set(id, item);
        this.patch({ items: merged, needRefresh: false });
        await this.refreshUnread();
      })
      .catch((error: unknown) => {
        this.assertCurrent(epoch, scope.generation);
        this.patch({ error, needRefresh: true });
        throw error;
      })
      .finally(() => {
        if (this.listPending === pending) {
          this.listPending = undefined;
          this.patch({ loading: false });
        }
      });
    this.listPending = pending;
    return pending;
  }

  refreshUnread(): Promise<void> {
    this.assertActive();
    const scope = this.options.session.capture();
    const epoch = this.epoch;
    if (this.countPending) return this.countPending;
    const pending = (async () => {
      // ponytail: 持续推送会连续合并计数请求，高吞吐场景应改用服务端游标快照。
      while (true) {
        const revision = this.revision;
        const count = countSchema.parse(
          await this.options.ports.unread(this.controller.signal),
        );
        this.assertCurrent(epoch, scope.generation);
        if (revision !== this.revision) continue;
        this.patch({ unreadCount: count });
        return;
      }
    })().finally(() => {
      if (this.countPending === pending) this.countPending = undefined;
    });
    this.countPending = pending;
    return pending;
  }

  subscribe(listener: () => void) {
    const stop = watch(this.state, listener);
    this.subscriptions.add(stop);
    return () => {
      stop();
      this.subscriptions.delete(stop);
    };
  }

  private assertActive() {
    if (this.disposed)
      throw new DOMException('通知实例已关闭', 'InvalidStateError');
  }
  private assertCurrent(epoch: number, generation: string) {
    if (
      this.disposed ||
      this.epoch !== epoch ||
      this.options.session.capture().generation !== generation
    )
      throw new DOMException('通知操作已失效', 'AbortError');
  }
  private onAvailability = () => this.syncPolling();
  private onDispose = () => this.dispose();
  private patch(values: Partial<typeof this.state.value>) {
    this.state.value = { ...this.state.value, ...values };
  }
  private persistSeen() {
    try {
      this.options.storage.setItem(
        this.options.storageKey,
        JSON.stringify({
          generation: this.options.session.capture().generation,
          ids: [...this.seen],
        }),
      );
    } catch (error) {
      this.options.ports.onError(error);
    }
  }
  private remember(id: string) {
    this.seen.add(id);
    if (this.seen.size > 512)
      this.seen.delete(this.seen.values().next().value as string);
    this.persistSeen();
  }
  private requestCount() {
    if (!this.countPending)
      void this.refreshUnread().catch((error: unknown) => {
        if (
          this.disposed ||
          (error instanceof DOMException && error.name === 'AbortError')
        )
          return;
        this.patch({ error, needRefresh: true });
        this.options.ports.onError(error);
      });
  }
  private restoreSeen() {
    const text = this.options.storage.getItem(this.options.storageKey);
    if (text === null) return;
    let value: unknown;
    try {
      value = JSON.parse(text);
    } catch {
      this.options.storage.removeItem(this.options.storageKey);
      this.options.ports.onError(new Error('通知去重缓存已损坏并清除'));
      return;
    }
    const result = dedupSchema.safeParse(value);
    if (!result.success) {
      this.options.storage.removeItem(this.options.storageKey);
      this.options.ports.onError(new Error('通知去重缓存格式无效并清除'));
      return;
    }
    if (result.data.generation === this.options.session.capture().generation)
      this.seen = new Set(result.data.ids);
  }
  private syncPolling() {
    const token = this.disposed ? null : this.options.session.capture().token;
    clearInterval(this.polling);
    this.polling = undefined;
    if (
      !this.disposed &&
      token !== null &&
      navigator.onLine &&
      document.visibilityState === 'visible'
    ) {
      this.polling = setInterval(
        () => this.requestCount(),
        this.options.pollIntervalMs,
      );
    }
  }
}
