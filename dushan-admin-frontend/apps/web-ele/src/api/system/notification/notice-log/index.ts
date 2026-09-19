import type { PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 通知推送日志端点（`/system/notification/log`）。ID 均为雪花字符串。 */
export namespace SystemNoticeLogApi {
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

  /** 推送日志信息 RespVO */
  export interface NoticeLogRespVO {
    createTime: string;
    failCount: number;
    id: string;
    noticeId: string;
    noticeTitle: string;
    noticeType: number;
    publisherInfo?: NoticePublisherInfoVO;
    pushChannels: string[];
    pushStatus: number;
    pushTargetType: number;
    successCount: number;
    targetDeptIds?: string[];
    targetDeptNames?: string[];
    targetUserIds?: string[];
    totalCount: number;
  }

  /** 推送日志分页查询 ReqVO */
  export interface NoticeLogPageReqVO extends PageParam {
    createTime?: string[];
    noticeId?: string;
    noticeTitle?: string;
    noticeType?: number;
    pushStatus?: number;
    pushTargetType?: number;
  }

  /** 推送日志消息明细 VO */
  export interface NoticeLogMessageVO {
    createTime: string;
    id: string;
    nickname?: string;
    readStatus: boolean;
    readTime?: string;
    userId: string;
    username?: string;
    userType: number;
  }

  /** 推送日志详情 RespVO（含消息明细） */
  export interface NoticeLogDetailRespVO extends NoticeLogRespVO {
    messages?: NoticeLogMessageVO[];
  }
}

/** 获得通知日志分页 */
export async function getNoticeLogPage(
  params: SystemNoticeLogApi.NoticeLogPageReqVO,
) {
  return requestClient.get<PageResult<SystemNoticeLogApi.NoticeLogRespVO>>(
    '/system/notification/log/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 获得通知日志详情（含消息明细） */
export async function getNoticeLogDetail(id: string) {
  return requestClient.get<SystemNoticeLogApi.NoticeLogDetailRespVO>(
    `/system/notification/log/get?id=${encodeURIComponent(id)}`,
  );
}
