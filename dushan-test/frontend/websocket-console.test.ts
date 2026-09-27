import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { createApp, h, KeepAlive, nextTick, ref } from 'vue';
import { createPinia } from 'pinia';
import { useAccessStore } from '@vben/stores';

import { SessionCoordinator } from '../../dushan-admin-frontend/apps/web-ele/src/services/session/coordinator';
import { useWebSocketTest } from '../../dushan-admin-frontend/apps/web-ele/src/views/infra/webSocket/composables/use-websocket-test';

const stubs = vi.hoisted(() => ({
  session: vi.fn(),
  ticket: vi.fn(),
  status: vi.fn(),
  broadcast: vi.fn(),
  sendToUser: vi.fn(),
  success: vi.fn(),
  warning: vi.fn(),
  queryOnly: false,
}));
vi.mock('#/services/session/runtime', () => ({ getSession: stubs.session }));
vi.mock('#/services/realtime-ports', () => ({
  getWebSocketTicket: stubs.ticket,
}));
vi.mock('#/api/infra/websocket', () => ({
  getWebSocketStatus: stubs.status,
  broadcastWebSocketMessage: stubs.broadcast,
  sendWebSocketMessageToUser: stubs.sendToUser,
}));
vi.mock('#/api/system/user', () => ({
  getSimpleUserList: async () => [{ id: '10100000010001', nickname: '管理员' }],
}));
vi.mock('#/api/error-feedback', () => ({ notifyError: vi.fn() }));
vi.mock('element-plus', () => ({
  ElMessage: { success: stubs.success, warning: stubs.warning, info: vi.fn() },
  ElNotification: vi.fn(),
}));

class TestSocket extends EventTarget {
  static instances: TestSocket[] = [];
  closed = false;
  constructor(readonly url: string) {
    super();
    TestSocket.instances.push(this);
    queueMicrotask(() => {
      this.dispatchEvent(new Event('open'));
      this.receive({
        type: 'connect',
        payload: { audience: new URL(url).searchParams.get('audience') },
      });
    });
  }
  receive(message: object) {
    this.dispatchEvent(
      new MessageEvent('message', {
        data: JSON.stringify({ timestamp: Date.now(), ...message }),
      }),
    );
  }
  send(body: string) {
    const message = JSON.parse(body);
    if (message.type === 'ping')
      this.receive({ type: 'pong', requestId: message.requestId });
    else {
      expect(['get-user-info', 'get-app-config']).toContain(message.type);
      this.receive({
        type: `${message.type}-response`,
        payload: { data: { ok: true } },
      });
    }
  }
  close() {
    this.closed = true;
  }
}

const cleanup: Array<() => void> = [];
beforeEach(() => {
  vi.stubEnv('VITE_WEBSOCKET_ENABLED', 'true');
  vi.stubEnv('VITE_WEBSOCKET_PATH', '/api/ws');
  vi.stubGlobal('WebSocket', TestSocket);
  vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(true);
  vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible');
  TestSocket.instances = [];
  stubs.queryOnly = false;
  const session = new SessionCoordinator({
    read: () => ({ generation: 'one', token: 'test' }),
    write: () => {},
    refresh: async () => 'test',
    expire: async () => {},
    lock: (run) => run(),
    subscribe: () => () => {},
  });
  stubs.session.mockReturnValue(session);
  cleanup.push(() => session.dispose());
  stubs.ticket.mockResolvedValue({
    ticket: 'one-use',
    expiresAtMs: Date.now() + 60000,
  });
  stubs.status.mockImplementation(async () => ({
    enabled: true,
    path: '/api/ws',
    sender_type: 'local',
    login_required: true,
    active_connections: infraSockets().length,
  }));
  stubs.broadcast.mockImplementation(async ({ message }) => {
    for (const socket of infraSockets())
      socket.receive({ type: 'infra-message', payload: message });
    return { transport: 'local', accepted: infraSockets().length };
  });
  stubs.sendToUser.mockImplementation(async ({ userId, message }) => {
    const targets = userId === '10100000010001' ? infraSockets() : [];
    for (const socket of targets)
      socket.receive({ type: 'infra-message', payload: message });
    return { transport: 'local', accepted: targets.length };
  });
});
afterEach(() => {
  for (const dispose of cleanup.splice(0).reverse()) dispose();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  vi.clearAllMocks();
});
function infraSockets() {
  return TestSocket.instances.filter(
    (s) => !s.closed && new URL(s.url).searchParams.get('audience') === 'infra',
  );
}
function mountPage() {
  const visible = ref(true);
  let page!: ReturnType<typeof useWebSocketTest>;
  const Page = {
    setup() {
      page = useWebSocketTest();
      return () => h('div');
    },
  };
  const app = createApp({
    setup: () => () =>
      h(KeepAlive, null, {
        default: () => (visible.value ? h(Page) : h('div')),
      }),
  });
  const pinia = createPinia();
  useAccessStore(pinia).setAccessCodes(
    stubs.queryOnly
      ? ['infra:websocket:query']
      : ['infra:websocket:query', 'infra:websocket:send'],
  );
  app.use(pinia);
  app.mount(document.createElement('div'));
  cleanup.push(() => app.unmount());
  return { page, visible };
}

it('独立连接infra，广播与定向进入接收日志，离开页面不影响system连接', async () => {
  const system = new TestSocket(
    'ws://localhost/api/ws?audience=system&ticket=global',
  );
  const { page, visible } = mountPage();
  await vi.waitFor(() =>
    expect(page.statusInfo.value?.active_connections).toBe(1),
  );
  expect(stubs.ticket).toHaveBeenCalledTimes(1);
  await page.sendBroadcast();
  await page.sendToUser();
  await vi.waitFor(() =>
    expect(
      page.receivedLogs.value.filter((l) =>
        l.message.includes('infra-message'),
      ),
    ).toHaveLength(2),
  );
  visible.value = false;
  await nextTick();
  expect(infraSockets()).toHaveLength(0);
  expect(system.closed).toBe(false);
  visible.value = true;
  await nextTick();
  await vi.waitFor(() => expect(infraSockets()).toHaveLength(1));
  expect(stubs.ticket).toHaveBeenCalledTimes(2);
});

it('直连示例符合协议，手动心跳有日志，零接受不会报发送成功', async () => {
  const { page } = mountPage();
  await vi.waitFor(() => expect(page.isConnected.value).toBe(true));
  page.sendDirectMessage();
  page.applyPreset('get-user-info');
  page.sendDirectMessage();
  page.applyPreset('get-app-config');
  page.sendDirectMessage();
  await vi.waitFor(() =>
    expect(
      page.receivedLogs.value.some((l) => l.message.includes('收到心跳响应')),
    ).toBe(true),
  );
  expect(
    page.receivedLogs.value.some((l) =>
      l.message.includes('get-user-info-response'),
    ),
  ).toBe(true);
  page.selectedUserId.value = '10100000019999';
  await page.sendToUser();
  expect(stubs.success).not.toHaveBeenCalled();
  expect(stubs.warning).toHaveBeenCalledWith('没有匹配的在线连接，消息未投递');
});

it('查询权限不会被当作发送权限', async () => {
  stubs.queryOnly = true;
  const { page } = mountPage();
  expect(page.canQuery.value).toBe(true);
  expect(page.canSend.value).toBe(false);
  await page.sendBroadcast();
  expect(stubs.broadcast).not.toHaveBeenCalled();
});
