import type { PageParam } from '#/api/types';

import { requestClient } from '#/api/request';

/** 在线用户端点（`/infra/online`）。 */
export namespace InfraOnlineApi {
  /** 在线用户信息 RespVO */
  export interface OnlineInfoRespVO {
    browser?: string;
    deptName?: string;
    ipaddr?: string;
    loginLocation?: string;
    loginTime?: string;
    os?: string;
    tokenId?: string;
    userName?: string;
  }

  /** 在线用户查询 ReqVO */
  export interface OnlineInfoReqVO extends PageParam {
    ipaddr?: string;
    userName?: string;
  }
}

/** 获取在线用户列表 */
export async function getOnlineList(params: InfraOnlineApi.OnlineInfoReqVO) {
  return requestClient.get<InfraOnlineApi.OnlineInfoRespVO[]>(
    '/infra/online/list',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 强制退出在线用户 */
export async function forceLogout(tokenId: string) {
  return requestClient.delete('/infra/online/force-logout', {
    params: { tokenId },
  });
}
