import type { PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 短信渠道端点（`/system/sms/channel`）。ID 均为雪花字符串。 */
export namespace SystemSmsChannelApi {
  /** 短信渠道信息 RespVO */
  export interface SmsChannelRespVO {
    apiKey: string;
    apiSecret?: string;
    callbackUrl?: string;
    code: string;
    createTime: string;
    id: string;
    remark?: string;
    signature: string;
    status: number;
  }

  /** 短信渠道创建/修改 ReqVO */
  export interface SmsChannelSaveReqVO {
    apiKey: string;
    apiSecret?: string;
    callbackUrl?: string;
    code: string;
    id?: string;
    remark?: string;
    signature: string;
    status: number;
  }

  /** 短信渠道分页查询 ReqVO */
  export interface SmsChannelPageReqVO extends PageParam {
    code?: string;
    createTime?: string[];
    signature?: string;
    status?: number;
  }

  /** 短信渠道精简信息 */
  export interface SmsChannelSimpleRespVO {
    code: string;
    id: string;
    signature: string;
  }
}

/** 创建短信渠道 */
export async function createSmsChannel(
  data: SystemSmsChannelApi.SmsChannelSaveReqVO,
) {
  return requestClient.post('/system/sms/channel/create', data);
}

/** 更新短信渠道 */
export async function updateSmsChannel(
  data: SystemSmsChannelApi.SmsChannelSaveReqVO,
) {
  return requestClient.put('/system/sms/channel/update', data);
}

/** 修改短信渠道状态 */
export async function updateSmsChannelStatus(id: string, status: number) {
  return requestClient.put('/system/sms/channel/update-status', {
    id,
    status,
  });
}

/** 删除短信渠道 */
export async function deleteSmsChannel(id: string) {
  return requestClient.delete(
    `/system/sms/channel/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 批量删除短信渠道 */
export async function deleteSmsChannelList(ids: string[]) {
  return requestClient.delete('/system/sms/channel/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}

/** 获得短信渠道 */
export async function getSmsChannel(id: string) {
  return requestClient.get<SystemSmsChannelApi.SmsChannelRespVO>(
    `/system/sms/channel/get?id=${encodeURIComponent(id)}`,
  );
}

/** 获得短信渠道分页 */
export async function getSmsChannelPage(
  params: SystemSmsChannelApi.SmsChannelPageReqVO,
) {
  return requestClient.get<PageResult<SystemSmsChannelApi.SmsChannelRespVO>>(
    '/system/sms/channel/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 获得短信渠道精简列表 */
export async function getSimpleSmsChannelList() {
  return requestClient.get<SystemSmsChannelApi.SmsChannelSimpleRespVO[]>(
    '/system/sms/channel/simple-list',
  );
}
