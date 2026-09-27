import { requestClient } from '#/api/request';

/** WebSocket 管理端点（`/infra/websocket`）。 */
export namespace InfraWebSocketApi {
  /** WebSocket 消息体 */
  export interface WebsocketMessageVO {
    payload?: unknown;
    requestId?: string;
    type: string;
  }

  /** 广播消息 ReqVO */
  export interface WebsocketBroadcastReqVO {
    message: string | WebsocketMessageVO;
  }

  /** 定向发送 ReqVO */
  export interface WebsocketSendToUserReqVO {
    message: string | WebsocketMessageVO;
    userId: string;
    userType: number;
  }

  /** WebSocket 状态信息（由服务层动态返回） */
  export interface WebsocketStatusVO {
    active_connections: number;
    enabled: boolean;
    login_required: boolean;
    path: string;
    sender_type: string;
  }

  export interface SocketReceipt {
    accepted: number;
    transport: 'local' | 'redis';
  }
}

/** 获取 WebSocket 状态 */
export async function getWebSocketStatus() {
  return requestClient.get<InfraWebSocketApi.WebsocketStatusVO>(
    '/infra/websocket/status',
  );
}

/** 广播消息 */
export async function broadcastWebSocketMessage(
  data: InfraWebSocketApi.WebsocketBroadcastReqVO,
) {
  return requestClient.post<InfraWebSocketApi.SocketReceipt>(
    '/infra/websocket/broadcast',
    data,
  );
}

/** 发送消息给指定用户 */
export async function sendWebSocketMessageToUser(
  data: InfraWebSocketApi.WebsocketSendToUserReqVO,
) {
  return requestClient.post<InfraWebSocketApi.SocketReceipt>(
    '/infra/websocket/send-to-user',
    data,
  );
}
