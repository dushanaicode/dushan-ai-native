import type { PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** OAuth2 客户端端点（`/system/oauth2/client`）。ID 均为雪花字符串。 */
export namespace SystemOAuth2ClientApi {
  /** OAuth2 客户端信息 RespVO */
  export interface OAuth2ClientRespVO {
    accessTokenValiditySeconds: number;
    additionalInformation?: string;
    authorities?: string[];
    authorizedGrantTypes: string[];
    autoApproveScopes?: string[];
    clientId: string;
    createTime: string;
    description?: string;
    id: string;
    logo: string;
    name: string;
    redirectUris: string[];
    refreshTokenValiditySeconds: number;
    resourceIds?: string[];
    scopes?: string[];
    secret: string;
    status: number;
  }

  /** OAuth2 客户端创建/修改 ReqVO */
  export interface OAuth2ClientSaveReqVO {
    accessTokenValiditySeconds: number;
    additionalInformation?: string;
    authorities?: string[];
    authorizedGrantTypes: string[];
    autoApproveScopes?: string[];
    clientId: string;
    description?: string;
    id?: string;
    logo: string;
    name: string;
    redirectUris: string[];
    refreshTokenValiditySeconds: number;
    resourceIds?: string[];
    scopes?: string[];
    secret?: string;
    status: number;
    userType?: number;
  }

  /** OAuth2 客户端分页查询 ReqVO */
  export interface OAuth2ClientPageReqVO extends PageParam {
    createTime?: string[];
    name?: string;
    status?: number;
  }
}

/** 创建 OAuth2 客户端 */
export async function createOAuth2Client(
  data: SystemOAuth2ClientApi.OAuth2ClientSaveReqVO,
) {
  return requestClient.post('/system/oauth2/client/create', data);
}

/** 更新 OAuth2 客户端 */
export async function updateOAuth2Client(
  data: SystemOAuth2ClientApi.OAuth2ClientSaveReqVO,
) {
  return requestClient.put('/system/oauth2/client/update', data);
}

/** 修改 OAuth2 客户端状态 */
export async function updateOAuth2ClientStatus(id: string, status: number) {
  return requestClient.put('/system/oauth2/client/update-status', {
    id,
    status,
  });
}

/** 删除 OAuth2 客户端 */
export async function deleteOAuth2Client(id: string) {
  return requestClient.delete(
    `/system/oauth2/client/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 批量删除 OAuth2 客户端 */
export async function deleteOAuth2ClientList(ids: string[]) {
  return requestClient.delete('/system/oauth2/client/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}

/** 获得 OAuth2 客户端 */
export async function getOAuth2Client(id: string) {
  return requestClient.get<SystemOAuth2ClientApi.OAuth2ClientRespVO>(
    `/system/oauth2/client/get?id=${encodeURIComponent(id)}`,
  );
}

/** 获得 OAuth2 客户端分页 */
export async function getOAuth2ClientPage(
  params: SystemOAuth2ClientApi.OAuth2ClientPageReqVO,
) {
  return requestClient.get<
    PageResult<SystemOAuth2ClientApi.OAuth2ClientRespVO>
  >('/system/oauth2/client/page', { params, paramsSerializer: 'repeat' });
}
