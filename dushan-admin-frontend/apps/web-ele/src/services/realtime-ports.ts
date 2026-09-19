import type { NotificationPorts } from './notifications/runtime';
import type { RealtimePorts } from './realtime';
import type { SocketTicket } from './websocket/connection';

import { requestClient } from '#/api/request';
import {
  getUnreadNoticeMessageCount,
  getUnreadNoticeMessageList,
  updateAllNoticeMessageRead,
  updateNoticeMessageRead,
} from '#/api/system/notification/notice-message';

import { buildSocketUrl, classifySocketClose } from './websocket/connection';
import { socketProtocol } from './websocket/protocol';

/** 后端 WebSocket 投递域（notice_socket_audience.py 注册 key=system） */
const AUDIENCE = 'system';
/** 票据本地保守有效期：55 秒（服务端一次性票据，过期即失效） */
const TICKET_TTL_MS = 55_000;

async function getTicket(signal: AbortSignal): Promise<SocketTicket> {
  const ticket = await requestClient.post<string>(
    '/system/auth/websocket-ticket',
    null,
    { signal },
  );
  return { ticket, expiresAtMs: Date.now() + TICKET_TTL_MS };
}

const notifications: Omit<NotificationPorts, 'notify' | 'onError'> = {
  list: async (signal) => {
    const items = await getUnreadNoticeMessageList(20, signal);
    return {
      items: items.map((item) => ({
        id: item.id,
        title: item.noticeTitle,
        content: item.noticeContent ?? '',
        createTime: item.createTime,
        isRead: item.readStatus,
      })),
      total: items.length,
    };
  },
  unread: (signal) => getUnreadNoticeMessageCount(signal),
  read: async (id, signal) => {
    await updateNoticeMessageRead([id], signal);
  },
  readAll: async (signal) => {
    await updateAllNoticeMessageRead(signal);
  },
};

export const realtimePorts: RealtimePorts = {
  getTicket,
  buildUrl: (base, ticket) => buildSocketUrl(base, ticket, AUDIENCE),
  classifyClose: classifySocketClose,
  protocol: socketProtocol,
  notifications,
  onError: (error) => console.error('[realtime]', error),
};
