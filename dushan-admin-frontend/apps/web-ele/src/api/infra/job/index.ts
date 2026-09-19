import type { ExportField, PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 定时任务端点（`/infra/job`）。ID 均为雪花字符串。 */
export namespace InfraJobApi {
  /** 定时任务信息 RespVO */
  export interface JobRespVO {
    createTime: string;
    cronExpression: string;
    handlerName: string;
    handlerParam?: string;
    id: string;
    monitorTimeout?: number;
    name: string;
    retryCount: number;
    retryInterval: number;
    status: number;
  }

  /** 定时任务创建/修改 ReqVO */
  export interface JobSaveReqVO {
    cronExpression: string;
    handlerName: string;
    handlerParam?: string;
    id?: string;
    monitorTimeout?: number;
    name: string;
    retryCount: number;
    retryInterval: number;
  }

  /** 定时任务分页查询 ReqVO */
  export interface JobPageReqVO extends PageParam {
    createTime?: string[];
    handlerName?: string;
    name?: string;
    status?: number;
  }
}

/** 创建定时任务 */
export async function createJob(data: InfraJobApi.JobSaveReqVO) {
  return requestClient.post('/infra/job/create', data);
}

/** 更新定时任务 */
export async function updateJob(data: InfraJobApi.JobSaveReqVO) {
  return requestClient.put('/infra/job/update', data);
}

/** 更新定时任务的状态 */
export async function updateJobStatus(id: string, status: number) {
  return requestClient.put('/infra/job/update-status', { id, status });
}

/** 删除定时任务 */
export async function deleteJob(id: string) {
  return requestClient.delete(`/infra/job/delete?id=${encodeURIComponent(id)}`);
}

/** 批量删除定时任务 */
export async function deleteJobList(ids: string[]) {
  return requestClient.delete('/infra/job/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}

/** 触发定时任务 */
export async function triggerJob(id: string) {
  return requestClient.put('/infra/job/trigger', null, { params: { id } });
}

/** 同步定时任务 */
export async function syncJob() {
  return requestClient.post('/infra/job/sync');
}

/** 获得定时任务 */
export async function getJob(id: string) {
  return requestClient.get<InfraJobApi.JobRespVO>(
    `/infra/job/get?id=${encodeURIComponent(id)}`,
  );
}

/** 获得定时任务分页 */
export async function getJobPage(params: InfraJobApi.JobPageReqVO) {
  return requestClient.get<PageResult<InfraJobApi.JobRespVO>>(
    '/infra/job/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 获取定时任务可导出字段列表 */
export async function getExportJobFields() {
  return requestClient.get<ExportField[]>('/infra/job/export-fields');
}

/** 导出定时任务 Excel */
export async function exportJob(params: InfraJobApi.JobPageReqVO) {
  return requestClient.download('/infra/job/export-excel', {
    params,
    paramsSerializer: 'repeat',
  });
}

/** 获得定时任务的下 n 次执行时间 */
export async function getJobNextTimes(id: string, count = 5) {
  return requestClient.get<string[]>('/infra/job/get_next_times', {
    params: { count, id },
  });
}
