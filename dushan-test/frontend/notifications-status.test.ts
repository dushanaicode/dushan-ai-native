import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  NotificationRuntime,
  type NotificationRecord,
} from '../../dushan-admin-frontend/apps/web-ele/src/services/notifications/runtime';
import { SessionCoordinator } from '../../dushan-admin-frontend/apps/web-ele/src/services/session/coordinator';
import {
  bindStatusRows,
  StatusRegistry,
} from '../../dushan-admin-frontend/apps/web-ele/src/services/websocket/status-sync';

const cleanup: Array<() => void> = [];
beforeEach(() => {
  vi.useFakeTimers();
  sessionStorage.clear();
});
afterEach(() => {
  for (const dispose of cleanup.splice(0)) dispose();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

const notice = (id: string): NotificationRecord => ({
  id,
  title: '标题',
  content: '<img src=x onerror=alert(1)>',
  createTime: '2026-09-13T00:00:00Z',
  isRead: false,
});

function fixture() {
  let snapshot = { generation: 'first', token: 'token' as null | string };
  const session = new SessionCoordinator({
    read: () => snapshot,
    write: (next) => {
      snapshot = { ...next };
    },
    refresh: async () => 'new',
    expire: async () => {},
    lock: (operation) => operation(),
    subscribe: () => () => {},
  });
  let count = 2;
  const ports = {
    list: vi.fn(async (_signal: AbortSignal): Promise<unknown> => ({
      items: [],
      total: 0,
    })),
    unread: vi.fn(async (_signal: AbortSignal): Promise<unknown> => count),
    read: vi.fn(async (_id: string, _signal: AbortSignal) => {
      count -= 1;
    }),
    readAll: vi.fn(async (_signal: AbortSignal) => {
      count = 0;
    }),
    notify: vi.fn(),
    onError: vi.fn(),
  };
  const make = () =>
    new NotificationRuntime({
      session,
      ports,
      storage: sessionStorage,
      storageKey: 'notice-test',
      recentLimit: 20,
      pollIntervalMs: 120_000,
    });
  const notifications = make();
  cleanup.push(() => {
    notifications.dispose();
    session.dispose();
  });
  return {
    notifications,
    ports,
    session,
    make,
    changeExternal: () => {
      snapshot = { generation: crypto.randomUUID(), token: 'external-token' };
    },
  };
}

describe('通知状态与故障边界', () => {
  it('入口先同步外部会话，再捕获操作代次，不复用旧缓存或误取消新请求', async () => {
    const { notifications, ports, changeExternal } = fixture();
    notifications.addNotification(
      Object.freeze({ ...notice('same'), isRead: true }),
    );
    changeExternal();
    ports.list.mockResolvedValue({ items: [notice('new')], total: 1 });
    await notifications.ensure();
    expect(notifications.notifications.map((item) => item.id)).toEqual(['new']);
    await notifications.markRead('same');
    expect(ports.read).toHaveBeenCalledOnce();
    await vi.advanceTimersByTimeAsync(0);
    const timers = vi.getTimerCount();
    changeExternal();
    window.dispatchEvent(new Event('online'));
    expect(vi.getTimerCount()).toBe(timers);
  });

  it('推送新增有明确返回值，补拉与推送按 ID 合并，事件去重可恢复', async () => {
    const { notifications, ports, make } = fixture();
    const pending = Promise.withResolvers<unknown>();
    ports.list.mockReturnValue(pending.promise);
    const loading = notifications.refresh();
    const frame = {
      type: 'notification',
      timestamp: 0,
      requestId: 'event-1',
      payload: notice('one'),
    };
    expect(notifications.handle(frame)).toBe(true);
    expect(notifications.handle(frame)).toBe(false);
    expect(notifications.handle({ ...frame, requestId: 'event-2' })).toBe(
      false,
    );
    pending.resolve({ items: [notice('one'), notice('two')], total: 2 });
    await loading;
    expect(notifications.notifications.map((item) => item.id)).toEqual([
      'one',
      'two',
    ]);
    expect(ports.notify).toHaveBeenCalledOnce();
    expect(ports.notify.mock.calls[0]![0].content).toBe(frame.payload.content);
    notifications.dispose();
    const restored = make();
    cleanup.push(() => restored.dispose());
    expect(restored.handle(frame)).toBe(false);
  });

  it('已读接口失败保持原状态，成功才更新；全部已读也保留错误', async () => {
    const { notifications, ports } = fixture();
    notifications.addNotification(notice('one'));
    notifications.addNotification(notice('two'));
    const failure = new Error('拒绝已读');
    ports.read.mockRejectedValueOnce(failure);
    const first = notifications.markRead('one');
    expect(notifications.markRead('one')).toBe(first);
    await expect(first).rejects.toBe(failure);
    expect(
      notifications.notifications.find((item) => item.id === 'one')?.isRead,
    ).toBe(false);
    expect(notifications.unreadCount).toBe(2);
    await notifications.markRead('one');
    await vi.advanceTimersByTimeAsync(0);
    expect(
      notifications.notifications.find((item) => item.id === 'one')?.isRead,
    ).toBe(true);
    expect(notifications.unreadCount).toBe(1);
    ports.readAll.mockRejectedValueOnce(failure);
    await expect(notifications.markAllRead()).rejects.toBe(failure);
    expect(notifications.notifications.some((item) => !item.isRead)).toBe(true);
    await notifications.markAllRead();
    await vi.advanceTimersByTimeAsync(0);
    expect(notifications.notifications.every((item) => item.isRead)).toBe(true);
    expect(notifications.unreadCount).toBe(0);
  });

  it('计数在有并发推送时补取新值，不用旧快照覆盖', async () => {
    const { notifications, ports } = fixture();
    const pending = Promise.withResolvers<unknown>();
    ports.unread.mockReturnValueOnce(pending.promise).mockResolvedValueOnce(8);
    const count = notifications.refreshUnread();
    notifications.addNotification(notice('new'));
    pending.resolve(7);
    await count;
    expect(ports.unread).toHaveBeenCalledTimes(2);
    expect(notifications.unreadCount).toBe(8);
  });

  it('会话清理取消在途已读，旧完成不写入新会话；销毁后不轮询', async () => {
    const { notifications, ports, session } = fixture();
    notifications.addNotification(notice('one'));
    const pending = Promise.withResolvers<void>();
    ports.read.mockReturnValue(pending.promise);
    const operation = Promise.allSettled([notifications.markRead('one')]);
    const signal = ports.read.mock.calls[0]![1];
    session.replace('another');
    expect(signal.aborted).toBe(true);
    pending.resolve();
    expect((await operation)[0]?.status).toBe('rejected');
    expect(notifications.notifications).toEqual([]);
    notifications.dispose();
    const calls = ports.unread.mock.calls.length;
    document.dispatchEvent(new Event('visibilitychange'));
    window.dispatchEvent(new Event('online'));
    await vi.advanceTimersByTimeAsync(240_000);
    expect(ports.unread).toHaveBeenCalledTimes(calls);
  });

  it('去重记录最多512条，损坏缓存清除并报告，不阻断后续通知', async () => {
    const { notifications, ports, make } = fixture();
    for (let index = 0; index < 513; index++)
      notifications.handle({
        type: 'notification',
        timestamp: 0,
        requestId: `event-${index}`,
        payload: notice(`notice-${index}`),
      });
    await vi.advanceTimersByTimeAsync(0);
    expect(JSON.parse(sessionStorage.getItem('notice-test')!).ids).toHaveLength(
      512,
    );
    notifications.dispose();
    sessionStorage.setItem('notice-test', '{broken');
    const restored = make();
    cleanup.push(() => restored.dispose());
    expect(ports.onError).toHaveBeenCalled();
    expect(
      restored.handle({
        type: 'notification',
        timestamp: 0,
        requestId: 'new',
        payload: notice('new'),
      }),
    ).toBe(true);
    await vi.advanceTimersByTimeAsync(0);
  });
});

describe('状态变更订阅与行代次', () => {
  it('回调失败互不阻断，注销不会删除随后建立的新订阅组', async () => {
    const { session } = fixture();
    const registry = new StatusRegistry(session);
    cleanup.push(() => registry.dispose());
    const failure = new Error('回调失败');
    registry.onStatusChange('job', () => {
      throw failure;
    });
    const success = vi.fn();
    registry.onStatusChange('job', success);
    await expect(
      registry.dispatch({
        taskType: 'job',
        id: '1',
        generation: 1,
        status: 'progress',
      }),
    ).rejects.toMatchObject({ errors: [failure] });
    expect(success).toHaveBeenCalledOnce();
    const oldRelease = registry.onStatusChange('job', vi.fn());
    session.replace('new');
    const current = vi.fn();
    registry.onStatusChange('job', current);
    oldRelease();
    await registry.dispatch({
      taskType: 'job',
      id: '1',
      generation: 2,
      status: 'success',
    });
    expect(current).toHaveBeenCalledOnce();
  });

  it('低代次与同代次终态后的更新丢弃，大字符串 ID 与新代次保留', async () => {
    const { session } = fixture();
    const registry = new StatusRegistry(session);
    cleanup.push(() => registry.dispose());
    const row = {
      id: '9223372036854775807',
      generation: 2,
      status: 'progress',
    };
    const apply = vi.fn((target: typeof row, change: { status: string }) => {
      target.status = change.status;
    });
    const release = bindStatusRows({
      registry,
      taskType: 'job',
      getRows: () => [row],
      accepts: (change) => change.parentId === 'parent',
      getId: (item) => item.id,
      getVersion: (item) => ({
        generation: item.generation,
        terminal: item.status !== 'progress',
      }),
      apply,
    });
    cleanup.push(release);
    const event = (
      generation: number,
      status: 'failure' | 'progress' | 'success',
    ) =>
      registry.dispatch({
        taskType: 'job',
        id: row.id,
        generation,
        status,
        parentId: 'parent',
      });
    await registry.dispatch({
      taskType: 'job',
      id: row.id,
      generation: 3,
      status: 'success',
      parentId: 'other',
    });
    expect(apply).not.toHaveBeenCalled();
    await event(1, 'progress');
    expect(apply).not.toHaveBeenCalled();
    await event(3, 'success');
    expect(apply).toHaveBeenCalledOnce();
    await event(3, 'progress');
    await event(3, 'success');
    expect(apply).toHaveBeenCalledOnce();
    await event(4, 'progress');
    expect(apply).toHaveBeenCalledTimes(2);
    expect(row.status).toBe('progress');
  });
});
