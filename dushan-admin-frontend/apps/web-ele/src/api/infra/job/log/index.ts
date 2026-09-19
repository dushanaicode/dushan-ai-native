import type { ExportField, PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 定时任务日志端点（`/infra/job/log`）。ID 均为雪花字符串。 */
export namespace InfraJobLogApi {
  /** 定时任务日志信息 RespVO */
  export interface JobLogRespVO {
    beginTime: string;
    createTime: string;
    duration?: number;
    endTime?: string;
    executeIndex: number;
    handlerName: string;
    handlerParam?: string;
    id: string;
    jobId: string;
    result?: string;
    status: number;
  }

  /** 定时任务日志分页查询 ReqVO */
  export interface JobLogPageReqVO extends PageParam {
    beginTime?: string;
    endTime?: string;
    handlerName?: string;
    jobId?: string;
    status?: number;
  }
}

/** 获得定时任务日志 */
export async function getJobLog(id: string) {
  return requestClient.get<InfraJobLogApi.JobLogRespVO>(
    `/infra/job/log/get?id=${encodeURIComponent(id)}`,
  );
}

/** 获得定时任务日志分页 */
export async function getJobLogPage(params: InfraJobLogApi.JobLogPageReqVO) {
  return requestClient.get<PageResult<InfraJobLogApi.JobLogRespVO>>(
    '/infra/job/log/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 获取定时任务日志可导出字段列表 */
export async function getExportJobLogFields() {
  return requestClient.get<ExportField[]>('/infra/job/log/export-fields');
}

/** 导出定时任务日志 Excel */
export async function exportJobLog(params: InfraJobLogApi.JobLogPageReqVO) {
  return requestClient.download('/infra/job/log/export-excel', {
    params,
    paramsSerializer: 'repeat',
  });
}
