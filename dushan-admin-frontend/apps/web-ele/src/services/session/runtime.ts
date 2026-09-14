import { useAccessStore } from '@vben/stores';

import { SessionCoordinator } from './coordinator';

let session: SessionCoordinator;

export function setupSession(options: {
  expire: () => Promise<void>;
  namespace: string;
  refresh: (signal: AbortSignal) => Promise<string>;
}) {
  const access = useAccessStore();
  const key = `${options.namespace}:session`;
  if (localStorage.getItem(key) === null) {
    localStorage.setItem(key, `${crypto.randomUUID()}:${crypto.randomUUID()}`);
  }
  session = new SessionCoordinator({
    expire: options.expire,
    async lock(operation) {
      if (!navigator.locks)
        throw new Error('会话刷新需要支持 Web Locks 的安全浏览环境');
      return navigator.locks.request(`${key}:refresh`, operation);
    },
    read() {
      const marker = localStorage.getItem(key);
      if (marker === null) return { generation: 'cleared', token: null };
      access.$hydrate();
      return {
        generation: marker.split(':')[0] as string,
        token: access.accessToken,
      };
    },
    refresh: options.refresh,
    subscribe(listener) {
      const onStorage = (event: StorageEvent) => {
        if (
          event.storageArea === localStorage &&
          (event.key === key || event.key === null)
        )
          listener();
      };
      window.addEventListener('storage', onStorage);
      return () => window.removeEventListener('storage', onStorage);
    },
    write(snapshot) {
      access.setAccessToken(snapshot.token);
      access.$persist();
      // 标记只含随机代次；令牌继续使用现有 Pinia 持久化策略。
      localStorage.setItem(
        key,
        `${snapshot.generation}:${crypto.randomUUID()}`,
      );
    },
  });
  session.subscribe((snapshot) => access.setAccessToken(snapshot.token));
  session.install();
  return session;
}

export function getSession() {
  return session;
}
