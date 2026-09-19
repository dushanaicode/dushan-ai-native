import type { PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 社交客户端端点（`/system/social/client`）。ID 均为雪花字符串。 */
export namespace SystemSocialClientApi {
  /** 社交客户端认证配置（后端 `auth_config` 为 dict，字段按 provider 约定） */
  export interface SocialClientAuthConfig {
    alipayPublicKey?: null | string;
    authServerId?: null | string;
    clientOsType?: null | number;
    deviceId?: null | string;
    dingTalkCorpId?: null | string;
    dingTalkExclusiveCorpId?: null | string;
    dingTalkExclusiveLogin?: boolean;
    dingTalkOrgType?: null | string;
    domainPrefix?: null | string;
    extConfig?: Record<string, unknown>;
    kid?: null | string;
    lang?: string;
    loginType?: string;
    packId?: null | string;
    pkce?: boolean;
    redirectUri?: string;
    scopes?: null | string[];
    stackOverflowKey?: null | string;
    teamId?: null | string;
    tenantId?: null | string;
    unionId?: boolean;
    usertype?: null | string;
  }

  /** 社交客户端信息 RespVO */
  export interface SocialClientRespVO {
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
    clientSecret: string;
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
