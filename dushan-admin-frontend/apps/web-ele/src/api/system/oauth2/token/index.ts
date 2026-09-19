import type { PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** OAuth2 令牌端点（`/system/oauth2/token`）。ID 均为雪花字符串。 */
export namespace SystemOAuth2TokenApi {
  /** 访问令牌信息 RespVO（仅元数据，令牌本体不可恢复） */
  export interface OAuth2AccessTokenRespVO {
    clientId: string;
    createTime: string;
    expiresTime: string;
    familyId: string;
    id: string;
    refreshTokenId?: string;
    revoked: boolean;
    scopes?: string[];
    userId: string;
    userType: number;
  }

  /** 访问令牌分页查询 ReqVO */
  export interface OAuth2AccessTokenPageReqVO extends PageParam {
    clientId?: string;
    createTime?: string[];
    userId?: string;
    userType?: number;
  }
}

/** 获得访问令牌分页 */
export async function getAccessTokenPage(
  params: SystemOAuth2TokenApi.OAuth2AccessTokenPageReqVO,
) {
  return requestClient.get<
    PageResult<SystemOAuth2TokenApi.OAuth2AccessTokenRespVO>
  >('/system/oauth2/token/page', { params, paramsSerializer: 'repeat' });
}

/** 删除访问令牌 */
export async function deleteAccessToken(id: string) {
  return requestClient.delete(
    `/system/oauth2/token/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 批量删除访问令牌 */
export async function deleteAccessTokenList(ids: string[]) {
  return requestClient.delete('/system/oauth2/token/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}
