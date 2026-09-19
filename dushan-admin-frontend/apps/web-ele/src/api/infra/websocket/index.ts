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
  export type WebsocketStatusVO = Record<string, unknown>;
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
  return requestClient.post('/infra/websocket/broadcast', data);
}

/** 发送消息给指定用户 */
export async function sendWebSocketMessageToUser(
  data: InfraWebSocketApi.WebsocketSendToUserReqVO,
) {
  return requestClient.post('/infra/websocket/send-to-user', data);
}
