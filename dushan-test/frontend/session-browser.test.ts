import { afterEach, describe, expect, it, vi } from 'vitest';

import { setupSession } from '../../dushan-admin-frontend/apps/web-ele/src/services/session/runtime';

const { access, state } = vi.hoisted(() => {
  const state = {
    stored: 'old' as null | string,
    token: 'old' as null | string,
  };
  const access = {
    get accessToken() {
      return state.token;
    },
    setAccessToken(token: null | string) {
      state.token = token;
    },
    $hydrate: vi.fn(() => {
      state.token = state.stored;
    }),
    $persist: vi.fn(() => {
      state.stored = state.token;
    }),
  };
  return { access, state };
});

vi.mock('@vben/stores', () => ({ useAccessStore: () => access }));

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe('浏览器会话接线', () => {
  it('局域网 HTTP 缺少 randomUUID 时仍可启动、登录、同步和退出', () => {
    const getRandomValues = crypto.getRandomValues.bind(crypto);
    vi.stubGlobal('crypto', { getRandomValues });
    state.token = state.stored = null;
    const session = setupSession({
      namespace: 'lan-http',
      refresh: async () => 'refreshed',
      expire: async () => {},
    });
    const initial = session.capture().generation;
    session.replace('lan-access-token');
    const loggedIn = session.capture();
    expect(loggedIn.token).toBe('lan-access-token');
    expect(loggedIn.generation).not.toBe(initial);
    expect(localStorage.getItem('lan-http:session')).not.toContain(
      'lan-access-token',
    );
    session.replace(null);
    expect(session.capture().token).toBeNull();
    expect(session.capture().generation).not.toBe(loggedIn.generation);
    session.dispose();
  });

  it('存储标记不含令牌，真实 storage 事件同步身份，dispose 移除监听', () => {
    state.token = state.stored = 'old';
    const session = setupSession({
      namespace: 'test-browser',
      refresh: async () => 'new',
      expire: async () => {},
    });
    const listener = vi.fn();
    session.subscribe(listener);
    session.replace('secret-access-token');
    const marker = localStorage.getItem('test-browser:session');
    expect(marker).not.toContain('secret-access-token');
    expect(state.stored).toBe('secret-access-token');
    state.stored = 'external-token';
    localStorage.setItem('test-browser:session', 'external:generation');
    window.dispatchEvent(
      new StorageEvent('storage', {
        key: 'test-browser:session',
        newValue: 'external:generation',
        storageArea: localStorage,
      }),
    );
    expect(session.capture().token).toBe('external-token');
    expect(listener).toHaveBeenCalledTimes(2);
    session.dispose();
    const hydrationCount = access.$hydrate.mock.calls.length;
    window.dispatchEvent(
      new StorageEvent('storage', {
        key: 'test-browser:session',
        storageArea: localStorage,
      }),
    );
    expect(access.$hydrate).toHaveBeenCalledTimes(hydrationCount);
  });

  it('不支持 Web Locks 时明确失败并且不调用刷新接口', async () => {
    state.token = state.stored = 'old';
    vi.stubGlobal('navigator', { locks: undefined });
    const refresh = vi.fn(async () => 'new');
    const expire = vi.fn(async () => {});
    const session = setupSession({ namespace: 'no-lock', refresh, expire });
    await expect(session.refresh()).rejects.toThrow('Web Locks');
    expect(refresh).not.toHaveBeenCalled();
    expect(expire).toHaveBeenCalledTimes(1);
    session.dispose();
  });
});
