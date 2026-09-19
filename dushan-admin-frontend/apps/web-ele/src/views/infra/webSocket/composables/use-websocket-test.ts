import type { InfraWebSocketApi } from '#/api/infra/websocket';
import type { SystemUserApi } from '#/api/system/user';
import type { SocketMessage } from '#/services/websocket/protocol';

import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

import { useAccess } from '@vben/access';
import { formatDate } from '@vben/utils';

import { ElMessage } from 'element-plus';

import {
  broadcastWebSocketMessage,
  getWebSocketStatus,
  sendWebSocketMessageToUser,
} from '#/api/infra/websocket';
import { getSimpleUserList } from '#/api/system/user';
import { useRealtime } from '#/services/realtime';
import { getSession } from '#/services/session/runtime';

export const WEBSOCKET_QUERY_PERMISSION = 'infra:websocket:query';

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
      payload: { client_timestamp: new Date().toISOString() },
      type: 'ping',
    }),
    label: '心跳检测',
    value: 'ping',
  },
  {
    createMessage: () => ({
      payload: {},
      type: 'get_user_info',
    }),
    label: '获取用户信息',
    value: 'get_user_info',
  },
  {
    createMessage: () => ({
      payload: {},
      type: 'get_app_config',
    }),
    label: '获取应用配置',
    value: 'get_app_config',
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
  const realtime = useRealtime();
  const socket = realtime?.socket;

  const canQuery = computed(() =>
    hasAccessByCodes([WEBSOCKET_QUERY_PERMISSION]),
  );
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
    socket
      ? `${window.location.origin}${import.meta.env.VITE_WEBSOCKET_PATH}（票据握手）`
      : '',
  );
  const maskedConnectionUrl = connectionUrl;

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
      ElMessage.error('服务状态刷新失败');
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

    void socket.connect();
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
      ElMessage.error(String(error));
      addLog('error', `直连消息发送失败: ${String(error)}`);
    }
  }

  async function sendBroadcast() {
    if (!ensureCanQuery('广播')) {
      return;
    }

    sending.value = true;
    try {
      const message = parseJsonMessage(broadcastMessage.value);
      await broadcastWebSocketMessage({ message });
      addLog('sent', `HTTP 广播发送: ${stringifyMessage(message)}`);
      ElMessage.success('广播消息已发送');
    } catch (error) {
      addLog('error', `广播消息发送失败: ${String(error)}`);
      ElMessage.error('广播消息发送失败');
    } finally {
      sending.value = false;
    }
  }

  async function sendToUser() {
    if (!ensureCanQuery('发送')) {
      return;
    }
    if (!selectedUserId.value) {
      ElMessage.warning('请选择目标用户');
      return;
    }

    sending.value = true;
    try {
      const message = parseJsonMessage(targetUserMessage.value);
      await sendWebSocketMessageToUser({
        message,
        userId: selectedUserId.value,
        userType: targetUserType.value,
      });
      addLog(
        'sent',
        `HTTP 定向发送给用户 ${selectedUserId.value}: ${stringifyMessage(message)}`,
      );
      ElMessage.success('用户消息已发送');
    } catch (error) {
      addLog('error', `用户消息发送失败: ${String(error)}`);
      ElMessage.error('用户消息发送失败');
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
    if (message.type === 'pong') {
      const payload = (message.payload ?? {}) as Record<string, unknown>;
      addLog(
        'received',
        `收到心跳响应: ${stringifyMessage({
          clientTimestamp: payload.client_timestamp,
          serverTimestamp: payload.server_timestamp,
        })}`,
      );
      return;
    }

    addLog('received', `收到消息: ${stringifyMessage(message)}`);
  }

  let unsubscribe: (() => void) | undefined;
  onMounted(async () => {
    if (socket) {
      unsubscribe = socket.on('*', handleMessage);
    }

    await Promise.all([loadUsers(), refreshStatus()]);

    if (socket && !isConnected.value && getSession().capture().token !== null) {
      void socket.connect();
      addLog('system', 'WebSocket 测试页面已触发连接');
    }
  });

  onBeforeUnmount(() => {
    unsubscribe?.();
  });

  return {
    applyPreset,
    broadcastMessage,
    canQuery,
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
