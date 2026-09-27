import type { AuthApi } from '#/api/core/auth';
import type { PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 社交客户端端点（`/system/social/client`）。ID 均为雪花字符串。 */
export namespace SystemSocialClientApi {
  /**
   * 社交客户端认证配置（后端 `auth_config`）。
   *
   * 字段名与后端契约一致，使用下划线，多余字段会被后端拒绝（业务码 1002032014）。
   * 渠道差异放在 `options`（如企业微信的 `agent_id`、`lang`），厂商凭据放在 `credentials`
   * （如支付宝的 `alipay_public_key`）；`credentials` 在查询响应中会被脱敏移除，
   * 更新时不提交即保留原值。
   */
  export interface SocialClientAuthConfig {
    credentials?: Record<string, string>;
    options?: Record<string, string>;
    pkce?: boolean;
    redirect_uri?: null | string;
    frontend_redirect_uri?: null | string;
    scopes?: string[];
  }

  /** 社交客户端信息 RespVO */
  export interface SocialClientRespVO {
    source?: string;
    agentId?: string;
    authConfig?: SocialClientAuthConfig;
    clientId?: string;
    clientSecret?: string;
    createTime?: string;
    id?: string;
    name?: string;
    socialType?: number;
    status?: number;
    userType?: number;
  }

  /** 社交客户端创建/修改 ReqVO */
  export interface SocialClientSaveReqVO {
    agentId?: string;
    authConfig?: SocialClientAuthConfig;
    clientId: string;
    clientSecret?: string;
    id?: string;
    name: string;
    socialType: number;
    status: number;
    userType: number;
  }

  /** 社交客户端分页查询 ReqVO */
  export interface SocialClientPageReqVO extends PageParam {
    clientId?: string;
    createTime?: string[];
    name?: string;
    socialType?: number;
    status?: number;
    userType?: number;
  }

  /** 发送订阅消息 ReqVO */
  export interface SubscribeMessageSendReqVO {
    messages?: Record<string, string>;
    page?: string;
    templateTitle: string;
    userId: string;
    userType: number;
  }
}

export async function getSocialProviderTypes() {
  return requestClient.get<AuthApi.SocialProvider[]>(
    '/system/social/client/types',
  );
}

/** 创建社交客户端 */
export async function createSocialClient(
  data: SystemSocialClientApi.SocialClientSaveReqVO,
) {
  return requestClient.post('/system/social/client/create', data);
}

/** 更新社交客户端 */
export async function updateSocialClient(
  data: SystemSocialClientApi.SocialClientSaveReqVO,
) {
  return requestClient.put('/system/social/client/update', data);
}

/** 修改社交客户端状态 */
export async function updateSocialClientStatus(id: string, status: number) {
  return requestClient.put('/system/social/client/update-status', {
    id,
    status,
  });
}

/** 删除社交客户端 */
export async function deleteSocialClient(id: string) {
  return requestClient.delete(
    `/system/social/client/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 批量删除社交客户端 */
export async function deleteSocialClientList(ids: string[]) {
  return requestClient.delete('/system/social/client/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}

/** 获得社交客户端 */
export async function getSocialClient(id: string) {
  return requestClient.get<SystemSocialClientApi.SocialClientRespVO>(
    `/system/social/client/get?id=${encodeURIComponent(id)}`,
  );
}

/** 获得社交客户端分页 */
export async function getSocialClientPage(
  params: SystemSocialClientApi.SocialClientPageReqVO,
) {
  return requestClient.get<
    PageResult<SystemSocialClientApi.SocialClientRespVO>
  >('/system/social/client/page', { params, paramsSerializer: 'repeat' });
}

/** 发送订阅消息 */
export async function sendSubscribeMessage(
  data: SystemSocialClientApi.SubscribeMessageSendReqVO,
) {
  return requestClient.post(
    '/system/social/client/send-subscribe-message',
    data,
  );
}
