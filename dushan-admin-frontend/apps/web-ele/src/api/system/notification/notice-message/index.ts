import type { PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 站内信端点（`/system/notification/message`）。ID 均为雪花字符串。 */
export namespace SystemNoticeMessageApi {
  /** 站内信发布者信息 */
  export interface NoticePublisherInfoVO {
    avatar?: string;
    browser?: string;
    deptId?: string;
    id?: string;
    ipaddr?: string;
    loginLocation?: string;
    loginTime?: string;
    nickname?: string;
    os?: string;
    username?: string;
  }

  /** 站内信信息 RespVO */
  export interface NoticeMessageRespVO {
    createTime: string;
    id: string;
    noticeContent?: string;
    noticeId: string;
    noticeTitle: string;
    noticeType: number;
    publisherInfo?: NoticePublisherInfoVO;
    readStatus: boolean;
    readTime?: string;
    userId: string;
    userType: number;
  }

  /** 站内信分页查询 ReqVO（管理员视图） */
  export interface NoticeMessagePageReqVO extends PageParam {
    createTime?: string[];
    noticeId?: string;
    noticeTitle?: string;
    noticeType?: number;
    readStatus?: boolean;
    userId?: string;
    userType?: number;
  }

  /** 我的站内信分页查询 ReqVO */
  export interface NoticeMessageMyPageReqVO extends PageParam {
    createTime?: string[];
    noticeTitle?: string;
    noticeType?: string;
    readStatus?: boolean;
  }
}

/** 获得站内信 */
export async function getNoticeMessage(id: string) {
  return requestClient.get<SystemNoticeMessageApi.NoticeMessageRespVO>(
    `/system/notification/message/get?id=${encodeURIComponent(id)}`,
  );
}

/** 获得站内信分页（管理员视图） */
export async function getNoticeMessagePage(
  params: SystemNoticeMessageApi.NoticeMessagePageReqVO,
) {
  return requestClient.get<
    PageResult<SystemNoticeMessageApi.NoticeMessageRespVO>
  >('/system/notification/message/page', {
    params,
    paramsSerializer: 'repeat',
  });
}

/** 获得我的站内信分页 */
export async function getMyNoticeMessagePage(
  params: SystemNoticeMessageApi.NoticeMessageMyPageReqVO,
) {
  return requestClient.get<
    PageResult<SystemNoticeMessageApi.NoticeMessageRespVO>
  >('/system/notification/message/my-page', {
    params,
    paramsSerializer: 'repeat',
  });
}

/** 获取未读站内信列表 */
export async function getUnreadNoticeMessageList(
  size = 10,
  signal?: AbortSignal,
) {
  return requestClient.get<SystemNoticeMessageApi.NoticeMessageRespVO[]>(
    '/system/notification/message/get-unread-list',
    { params: { size }, signal },
  );
}

/** 获得当前用户的未读站内信数量 */
export async function getUnreadNoticeMessageCount(signal?: AbortSignal) {
  return requestClient.get<number>(
    '/system/notification/message/get-unread-count',
    { signal },
  );
}

/** 标记站内信为已读（body: {ids}） */
export async function updateNoticeMessageRead(
  ids: string[],
  signal?: AbortSignal,
) {
  return requestClient.put(
    '/system/notification/message/update-read',
    { ids },
    { signal },
  );
}

/** 标记所有站内信为已读 */
export async function updateAllNoticeMessageRead(signal?: AbortSignal) {
  return requestClient.put(
    '/system/notification/message/update-all-read',
    null,
    { signal },
  );
}
