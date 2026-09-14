import type { App, InjectionKey } from 'vue';

import type { NotificationPorts } from './notifications/runtime';
import type { SessionCoordinator } from './session/coordinator';
import type { SocketTicket } from './websocket/connection';
import type { SocketProtocol } from './websocket/protocol';

import { inject } from 'vue';

import { ElNotification } from 'element-plus';

import { NotificationRuntime } from './notifications/runtime';
import { defaultSocketPolicy, SocketConnection } from './websocket/connection';
import { StatusRegistry } from './websocket/status-sync';

export interface RealtimePorts {
  getTicket: (signal: AbortSignal) => Promise<SocketTicket>;
  buildUrl: (base: URL, ticket: SocketTicket) => URL;
  classifyClose: (code: number) => 'auth' | 'limited' | 'retry' | 'stop';
  protocol: SocketProtocol;
  notifications: Omit<NotificationPorts, 'notify' | 'onError'>;
  onError: (error: unknown) => void;
}

export interface Realtime {
  socket: SocketConnection;
  notifications: NotificationRuntime;
  statuses: StatusRegistry;
  dispose: () => void;
}
const realtimeKey: InjectionKey<Realtime> = Symbol('realtime');

export function readRealtimeConfig(
  environment: { enabled: string; path: string },
  origin: string,
) {
  if (environment.enabled === 'false') return { enabled: false } as const;
  if (environment.enabled !== 'true')
    throw new TypeError('VITE_WEBSOCKET_ENABLED 必须是 true 或 false');
  const url = new URL(environment.path, origin);
  if (
    !environment.path.startsWith('/api/') ||
    url.origin !== origin ||
    url.search ||
    url.hash ||
    url.username ||
    url.password
  )
    throw new TypeError('VITE_WEBSOCKET_PATH 必须是同源 /api 下的路径');
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  return { enabled: true, url } as const;
}

export function installRealtime(options: {
  app: App;
  namespace: string;
  session: SessionCoordinator;
  environment: { enabled: string; path: string };
  origin: string;
  ports?: RealtimePorts;
}) {
  const config = readRealtimeConfig(options.environment, options.origin);
  if (!config.enabled) return;
  const ports = options.ports;
  if (!ports) throw new Error('启用实时功能必须提供真实接口端口');
  const socket = new SocketConnection({
    baseUrl: config.url,
    getTicket: ports.getTicket,
    buildUrl: ports.buildUrl,
    classifyClose: ports.classifyClose,
    protocol: ports.protocol,
    session: options.session,
    policy: defaultSocketPolicy,
    onError: ports.onError,
  });
  let notifications: NotificationRuntime | undefined;
  let statuses: StatusRegistry | undefined;
  try {
    notifications = new NotificationRuntime({
      session: options.session,
      storage: sessionStorage,
      storageKey: `${options.namespace}:notifications`,
      recentLimit: 20,
      pollIntervalMs: 120_000,
      ports: {
        ...ports.notifications,
        onError: ports.onError,
        notify: (notification) =>
          ElNotification({
            title: notification.title,
            message: notification.content,
            type: 'info',
          }),
      },
    });
    statuses = new StatusRegistry(options.session);
    const notificationRuntime = notifications;
    const statusRuntime = statuses;
    socket.on('notification', (message) => notificationRuntime.handle(message));
    socket.on('status-change', (message) =>
      statusRuntime.dispatch(message.payload),
    );
    socket.onConnected(() => notificationRuntime.refresh());
    const realtime: Realtime = {
      socket,
      notifications,
      statuses,
      dispose: () => {
        socket.dispose();
        notificationRuntime.dispose();
        statusRuntime.dispose();
      },
    };
    options.app.provide(realtimeKey, realtime);
    options.app.onUnmount(realtime.dispose);
    void socket.connect().catch(ports.onError);
    return realtime;
  } catch (error) {
    socket.dispose();
    notifications?.dispose();
    statuses?.dispose();
    throw error;
  }
}

export function useRealtime() {
  return inject(realtimeKey, undefined);
}
