import type { InfraWebSocketApi } from '#/api/infra/websocket';
import type { SystemUserApi } from '#/api/system/user';
import type { SocketMessage } from '#/services/websocket/protocol';

import {
  computed,
  onActivated,
  onBeforeUnmount,
  onDeactivated,
  onMounted,
  ref,
} from 'vue';

import { useAccess } from '@vben/access';
import { formatDate } from '@vben/utils';

import { ElMessage } from 'element-plus';

import { notifyError } from '#/api/error-feedback';
import {
  broadcastWebSocketMessage,
  getWebSocketStatus,
  sendWebSocketMessageToUser,
} from '#/api/infra/websocket';
import { getSimpleUserList } from '#/api/system/user';
import { readRealtimeConfig } from '#/services/realtime';
import { getWebSocketTicket } from '#/services/realtime-ports';
import { getSession } from '#/services/session/runtime';
import {
  buildSocketUrl,
  classifySocketClose,
  defaultSocketPolicy,
  SocketConnection,
} from '#/services/websocket/connection';
import { socketProtocol } from '#/services/websocket/protocol';
import { createRandomId } from '#/utils/random-id';

export const WEBSOCKET_QUERY_PERMISSION = 'infra:websocket:query';
export const WEBSOCKET_SEND_PERMISSION = 'infra:websocket:send';

/** SocketConnection 连接状态（小写） */
export type WebSocketConnectionStatus =
  | 'backoff'
  | 'closed'
  | 'connecting'
  | 'disposed'
  | 'exhausted'
  | 'idle'
  | 'open'
  | 'recovering'
  | 'ticket';

export type WebSocketTestContext = ReturnType<typeof useWebSocketTest>;

type LogType = 'error' | 'info' | 'received' | 'sent' | 'system';

export interface WebSocketTestLog {
  message: string;
  time: number;
  type: LogType;
}

interface MessagePreset {
  label: string;
  value: string;
  createMessage: () => InfraWebSocketApi.WebsocketMessageVO;
}

const DIRECT_MESSAGE_PRESETS: MessagePreset[] = [
  {
    createMessage: () => ({
      requestId: createRandomId(),
      type: 'ping',
    }),
    label: '心跳检测',
    value: 'ping',
  },
  {
    createMessage: () => ({
      payload: {},
      type: 'get-user-info',
    }),
    label: '获取用户信息',
    value: 'get-user-info',
  },
  {
    createMessage: () => ({
      payload: {},
      type: 'get-app-config',
    }),
    label: '获取应用配置',
    value: 'get-app-config',
  },
];

const defaultBroadcastMessage = {
  payload: {
    content: '系统将于 2 小时后进行维护',
    event: 'new_announcement',
    title: '系统通知',
  },
  type: 'broadcast',
};

const defaultUserMessage = {
  payload: {
    content: '您的会议即将开始',
    title: '私人提醒',
  },
  type: 'notice_message',
};

function stringifyMessage(message: unknown) {
  return JSON.stringify(message, null, 2);
}

function parseJsonMessage(
  content: string,
): InfraWebSocketApi.WebsocketMessageVO {
  const parsed = JSON.parse(content.trim()) as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new TypeError('消息内容必须是 JSON 对象');
  }
  if (typeof (parsed as { type?: unknown }).type !== 'string') {
    throw new TypeError('消息内容必须包含字符串类型的 type 字段');
  }
  return parsed as InfraWebSocketApi.WebsocketMessageVO;
}

async function copyText(text: string) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textArea = document.createElement('textarea');
  textArea.value = text;
  document.body.append(textArea);
  textArea.select();
  document.execCommand('copy');
  textArea.remove();
}

export function useWebSocketTest() {
  const { hasAccessByCodes } = useAccess();
  const config = readRealtimeConfig(
    {
      enabled: import.meta.env.VITE_WEBSOCKET_ENABLED,
      path: import.meta.env.VITE_WEBSOCKET_PATH,
    },
    window.location.origin,
  );
  const socket = config.enabled
    ? new SocketConnection({
        baseUrl: config.url,
        buildUrl: (base, ticket) => buildSocketUrl(base, ticket, 'infra'),
        getTicket: getWebSocketTicket,
        classifyClose: classifySocketClose,
        protocol: socketProtocol,
        session: getSession(),
        policy: defaultSocketPolicy,
        onError: handleConnectionError,
      })
    : undefined;

  const canQuery = computed(() =>
    hasAccessByCodes([WEBSOCKET_QUERY_PERMISSION]),
  );
  const canSend = computed(() => hasAccessByCodes([WEBSOCKET_SEND_PERMISSION]));
  const directMessage = ref(
    stringifyMessage(DIRECT_MESSAGE_PRESETS[0]?.createMessage() ?? {}),
  );
  const selectedPreset = ref(DIRECT_MESSAGE_PRESETS[0]?.value ?? '');
  const broadcastMessage = ref(stringifyMessage(defaultBroadcastMessage));
  const targetUserMessage = ref(stringifyMessage(defaultUserMessage));
  const targetUserType = ref(2);
  const selectedUserId = ref<string>();
  const users = ref<SystemUserApi.UserSimpleRespVO[]>([]);
  const statusInfo = ref<InfraWebSocketApi.WebsocketStatusVO>();
  const statusLoading = ref(false);
  const userLoading = ref(false);
  const sending = ref(false);
  const sentLogs = ref<WebSocketTestLog[]>([]);
  const receivedLogs = ref<WebSocketTestLog[]>([]);

  const wsStatus = computed(() => socket?.status ?? 'idle');
  const wsLastError = computed(() => socket?.error);
  const isConnected = computed(() => wsStatus.value === 'open');
  const websocketEnabled = computed(() => Boolean(socket));
  const connectionUrl = computed(() =>
    config.enabled ? `${config.url.href}?audience=infra（票据握手）` : '',
  );
  const maskedConnectionUrl = connectionUrl;

  function handleConnectionError(error: unknown) {
    addLog('error', `WebSocket 连接失败: ${String(error)}`);
  }

  function ensureCanSend() {
    if (canSend.value) return true;
    ElMessage.warning('当前账号没有 WebSocket 发送权限');
    return false;
  }

  function showReceipt(receipt: InfraWebSocketApi.SocketReceipt) {
    if (receipt.accepted === 0) {
      ElMessage.warning(
        receipt.transport === 'local'
          ? '没有匹配的在线连接，消息未投递'
          : '没有服务接收此次投递',
      );
      return;
    }
    ElMessage.success('消息已提交，实际接收请查看接收日志');
  }

  function addLog(type: LogType, message: string) {
    const log: WebSocketTestLog = {
      message,
      time: Date.now(),
      type,
    };

    if (type === 'sent') {
      sentLogs.value.push(log);
      return;
    }
    if (type === 'received') {
      receivedLogs.value.push(log);
      return;
    }

    sentLogs.value.push(log);
    receivedLogs.value.push(log);
  }

  function ensureCanQuery(action: string) {
    if (!canQuery.value) {
      ElMessage.warning(`当前账号没有 WebSocket ${action}权限`);
      return false;
    }
    return true;
  }

  function ensureConnected() {
    if (!isConnected.value) {
      ElMessage.warning('WebSocket 未连接');
      return false;
    }
    return true;
  }

  function applyPreset(value = selectedPreset.value) {
    const preset = DIRECT_MESSAGE_PRESETS.find((item) => item.value === value);
    if (!preset) {
      return;
    }
    selectedPreset.value = value;
    directMessage.value = stringifyMessage(preset.createMessage());
  }

  async function refreshStatus() {
    if (!ensureCanQuery('查询')) {
      return;
    }

    statusLoading.value = true;
    try {
      statusInfo.value = await getWebSocketStatus();
      addLog(
        'info',
        `服务状态刷新成功，当前连接数 ${statusInfo.value.active_connections}`,
      );
    } catch (error) {
      addLog('error', `服务状态刷新失败: ${String(error)}`);
      notifyError(error, '服务状态刷新失败');
    } finally {
      statusLoading.value = false;
    }
  }

  async function loadUsers() {
    userLoading.value = true;
    try {
      users.value = await getSimpleUserList();
      if (!selectedUserId.value && users.value[0]) {
        selectedUserId.value = users.value[0].id;
      }
      addLog('info', `用户精简列表加载成功，共 ${users.value.length} 个用户`);
    } catch (error) {
      addLog('error', `用户精简列表加载失败: ${String(error)}`);
    } finally {
      userLoading.value = false;
    }
  }

  function connectWebSocket() {
    if (!socket) {
      ElMessage.warning('实时连接未启用（VITE_WEBSOCKET_ENABLED=false）');
      return;
    }
    if (isConnected.value) {
      ElMessage.info('WebSocket 已连接');
      return;
    }

    void socket.connect().catch(handleConnectionError);
    addLog('system', `开始连接 ${maskedConnectionUrl.value}`);
  }

  function disconnectWebSocket() {
    if (!socket) {
      return;
    }
    if (!isConnected.value && wsStatus.value !== 'connecting') {
      ElMessage.info('WebSocket 当前未连接');
      return;
    }

    socket.disconnect();
    addLog('system', '已请求断开 WebSocket 连接');
  }

  function sendDirectMessage() {
    if (!ensureConnected() || !socket) {
      return;
    }

    try {
      const message = parseJsonMessage(directMessage.value);
      socket.send(message);
      addLog('sent', `直连发送: ${stringifyMessage(message)}`);
    } catch (error) {
      notifyError(error);
      addLog('error', `直连消息发送失败: ${String(error)}`);
    }
  }

  async function sendBroadcast() {
    if (!ensureCanSend()) {
      return;
    }

    sending.value = true;
    try {
      const message = parseJsonMessage(broadcastMessage.value);
      const receipt = await broadcastWebSocketMessage({ message });
      addLog(
        'sent',
        `HTTP 广播提交（${receipt.transport} 接受 ${receipt.accepted}）: ${stringifyMessage(message)}`,
      );
      showReceipt(receipt);
    } catch (error) {
      addLog('error', `广播消息发送失败: ${String(error)}`);
      notifyError(error, '广播消息发送失败');
    } finally {
      sending.value = false;
    }
  }

  async function sendToUser() {
    if (!ensureCanSend()) {
      return;
    }
    if (!selectedUserId.value) {
      ElMessage.warning('请选择目标用户');
      return;
    }

    sending.value = true;
    try {
      const message = parseJsonMessage(targetUserMessage.value);
      const receipt = await sendWebSocketMessageToUser({
        message,
        userId: selectedUserId.value,
        userType: targetUserType.value,
      });
      addLog(
        'sent',
        `HTTP 定向提交给用户 ${selectedUserId.value}（${receipt.transport} 接受 ${receipt.accepted}）: ${stringifyMessage(message)}`,
      );
      showReceipt(receipt);
    } catch (error) {
      addLog('error', `用户消息发送失败: ${String(error)}`);
      notifyError(error, '用户消息发送失败');
    } finally {
      sending.value = false;
    }
  }

  async function copyConnectionUrl() {
    await copyText(connectionUrl.value);
    ElMessage.success('连接地址已复制');
  }

  function clearSentLogs() {
    sentLogs.value = [];
  }

  function clearReceivedLogs() {
    receivedLogs.value = [];
  }

  function formatLogTime(time: number) {
    return formatDate(time, 'YYYY-MM-DD HH:mm:ss.SSS');
  }

  function getLogTagType(type: LogType) {
    const tagTypeMap: Record<
      LogType,
      'danger' | 'info' | 'primary' | 'success' | 'warning'
    > = {
      error: 'danger',
      info: 'info',
      received: 'success',
      sent: 'warning',
      system: 'primary',
    };
    return tagTypeMap[type];
  }

  function getLogTypeText(type: LogType) {
    const textMap: Record<LogType, string> = {
      error: '错误',
      info: '信息',
      received: '接收',
      sent: '发送',
      system: '系统',
    };
    return textMap[type];
  }

  function handleMessage(message: SocketMessage) {
    if (message.type === 'connect') void refreshStatus();
    if (message.type === 'pong') {
      addLog('received', `收到心跳响应: ${stringifyMessage(message)}`);
      return;
    }

    addLog('received', `收到消息: ${stringifyMessage(message)}`);
  }

  let unsubscribe: (() => void) | undefined;
  function activateConnection() {
    if (socket && !isConnected.value && getSession().capture().token !== null) {
      void socket.connect().catch(handleConnectionError);
    }
  }

  onMounted(() => {
    if (socket) {
      unsubscribe = socket.on('*', handleMessage);
    }

    void loadUsers();
    activateConnection();
    if (!socket) void refreshStatus();
  });

  onActivated(activateConnection);
  onDeactivated(() => socket?.disconnect());

  onBeforeUnmount(() => {
    unsubscribe?.();
    socket?.dispose();
  });

  return {
    applyPreset,
    broadcastMessage,
    canQuery,
    canSend,
    clearReceivedLogs,
    clearSentLogs,
    connectWebSocket,
    copyConnectionUrl,
    directMessage,
    disconnectWebSocket,
    formatLogTime,
    getLogTagType,
    getLogTypeText,
    isConnected,
    loadUsers,
    maskedConnectionUrl,
    presets: DIRECT_MESSAGE_PRESETS,
    receivedLogs,
    refreshStatus,
    selectedPreset,
    selectedUserId,
    sendBroadcast,
    sendDirectMessage,
    sending,
    sendToUser,
    sentLogs,
    statusInfo,
    statusLoading,
    targetUserMessage,
    targetUserType,
    userLoading,
    users,
    websocketEnabled,
    websocketPath: computed(() => statusInfo.value?.path || ''),
    wsBaseUrl: connectionUrl,
    wsLastError,
    wsStatus,
  };
}
