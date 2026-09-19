import type { PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 系统通知端点（`/system/notification/notice`）。ID 均为雪花字符串。 */
export namespace SystemNoticeApi {
  /** 通知信息 RespVO */
  export interface NoticeRespVO {
    builtin?: number;
    channels: string[];
    code?: string;
    content: string;
    createTime: string;
    id: string;
    mailAccountId?: string;
    publisher: string;
    smsTemplateCode?: string;
    status: number;
    title: string;
    type: number;
    userType: number;
  }

  /** 通知创建/修改 ReqVO */
  export interface NoticeSaveReqVO {
    channels: string[];
    content: string;
    id?: string;
    mailAccountId?: string;
    publisher?: string;
    smsTemplateCode?: string;
    status: number;
    title: string;
    type: number;
    userType: number;
  }

  /** 通知分页查询 ReqVO */
  export interface NoticePageReqVO extends PageParam {
    channels?: string[];
    createTime?: string[];
    publisher?: string;
    status?: number;
    title?: string;
    type?: number;
    userType?: number;
  }

  /** 定向推送 ReqVO */
  export interface NoticeSendReqVO {
    deptIds?: string[];
    id: string;
    userIds?: string[];
  }
}

/** 查询通知分页 */
export async function getNoticePage(params: SystemNoticeApi.NoticePageReqVO) {
  return requestClient.get<PageResult<SystemNoticeApi.NoticeRespVO>>(
    '/system/notification/notice/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 查询通知详情 */
export async function getNotice(id: string) {
  return requestClient.get<SystemNoticeApi.NoticeRespVO>(
    `/system/notification/notice/get?id=${encodeURIComponent(id)}`,
  );
}

/** 创建通知 */
export async function createNotice(data: SystemNoticeApi.NoticeSaveReqVO) {
  return requestClient.post('/system/notification/notice/create', data);
}

/** 更新通知 */
export async function updateNotice(data: SystemNoticeApi.NoticeSaveReqVO) {
  return requestClient.put('/system/notification/notice/update', data);
}

/** 修改通知状态 */
export async function updateNoticeStatus(id: string, status: number) {
  return requestClient.put('/system/notification/notice/update-status', {
    id,
    status,
  });
}

/** 删除通知 */
export async function deleteNotice(id: string) {
  return requestClient.delete(
    `/system/notification/notice/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 批量删除通知 */
export async function deleteNoticeList(ids: string[]) {
  return requestClient.delete('/system/notification/notice/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}

/** 定向推送系统通知 */
export async function pushNoticeToTargets(
  data: SystemNoticeApi.NoticeSendReqVO,
) {
  return requestClient.post('/system/notification/notice/push-targets', data);
}
