import type { PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 公告端点（`/system/announcement`）。ID 均为雪花字符串。 */
export namespace SystemAnnouncementApi {
  /** 公告信息 RespVO */
  export interface AnnouncementRespVO {
    category: number;
    content: string;
    createTime: string;
    expireTime?: string;
    id: string;
    isTop: boolean;
    publisher: string;
    publishTime?: string;
    sort: number;
    status: number;
    title: string;
  }

  /** 公告创建/修改 ReqVO */
  export interface AnnouncementSaveReqVO {
    category: number;
    content: string;
    expireTime?: string;
    id?: string;
    isTop?: boolean;
    publisher: string;
    publishTime?: string;
    sort?: number;
    status: number;
    title: string;
  }

  /** 公告分页查询 ReqVO */
  export interface AnnouncementPageReqVO extends PageParam {
    category?: number;
    createTime?: string[];
    isTop?: boolean;
    status?: number;
    title?: string;
  }
}

/** 获取公告分页 */
export async function getAnnouncementPage(
  params: SystemAnnouncementApi.AnnouncementPageReqVO,
) {
  return requestClient.get<
    PageResult<SystemAnnouncementApi.AnnouncementRespVO>
  >('/system/announcement/page', { params, paramsSerializer: 'repeat' });
}

/** 获取公告详情 */
export async function getAnnouncement(id: string) {
  return requestClient.get<SystemAnnouncementApi.AnnouncementRespVO>(
    `/system/announcement/get?id=${encodeURIComponent(id)}`,
  );
}

/** 创建公告 */
export async function createAnnouncement(
  data: SystemAnnouncementApi.AnnouncementSaveReqVO,
) {
  return requestClient.post('/system/announcement/create', data);
}

/** 更新公告 */
export async function updateAnnouncement(
  data: SystemAnnouncementApi.AnnouncementSaveReqVO,
) {
  return requestClient.put('/system/announcement/update', data);
}

/** 删除公告 */
export async function deleteAnnouncement(id: string) {
  return requestClient.delete(
    `/system/announcement/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 批量删除公告 */
export async function deleteAnnouncementList(ids: string[]) {
  return requestClient.delete('/system/announcement/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}

/** 立即发布公告 */
export async function publishAnnouncement(id: string) {
  return requestClient.post('/system/announcement/publish', null, {
    params: { id },
  });
}

/** 调度定时发布公告 */
export async function scheduleAnnouncement(id: string) {
  return requestClient.post('/system/announcement/schedule-publish', null, {
    params: { id },
  });
}
