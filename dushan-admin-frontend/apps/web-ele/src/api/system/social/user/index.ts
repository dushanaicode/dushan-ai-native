import type { PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 社交用户端点（`/system/social/user`）。ID 均为雪花字符串。 */
export namespace SystemSocialUserApi {
  /** 社交用户信息 RespVO */
  export interface SocialUserRespVO {
    avatar?: string;
    code: string;
    createTime: string;
    id?: string;
    nickname: string;
    openid: string;
    rawTokenInfo: string;
    rawUserInfo: string;
    state?: string;
    token?: string;
    type: number;
    updateTime: string;
  }

  /** 社交用户分页查询 ReqVO */
  export interface SocialUserPageReqVO extends PageParam {
    createTime?: string[];
    nickname?: string;
    openid?: string;
    type?: number;
  }
}

/** 社交绑定（使用 code 授权码） */
export async function bindSocialUser(data: {
  code: string;
  state: string;
  type: number;
}) {
  return requestClient.post<string>('/system/social/user/bind', data);
}

/** 取消社交绑定（body 传参） */
export async function unbindSocialUser(data: { openid: string; type: number }) {
  return requestClient.delete('/system/social/user/unbind', { data });
}

/** 获得社交用户 */
export async function getSocialUser(id: string) {
  return requestClient.get<SystemSocialUserApi.SocialUserRespVO>(
    `/system/social/user/get?id=${encodeURIComponent(id)}`,
  );
}

/** 获得社交用户分页 */
export async function getSocialUserPage(
  params: SystemSocialUserApi.SocialUserPageReqVO,
) {
  return requestClient.get<PageResult<SystemSocialUserApi.SocialUserRespVO>>(
    '/system/social/user/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 获得绑定社交用户列表 */
export async function getBindSocialUserList() {
  return requestClient.get<SystemSocialUserApi.SocialUserRespVO[]>(
    '/system/social/user/get-bind-list',
  );
}
