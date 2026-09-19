import type { ExportField, PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** API 错误日志端点（`/infra/logger/api-error-log`）。ID 均为雪花字符串。 */
export namespace InfraApiErrorLogApi {
  /** API 错误日志信息 RespVO */
  export interface ApiErrorLogRespVO {
    applicationName: string;
    createTime: string;
    exceptionClassName: string;
    exceptionFileName: string;
    exceptionLineNumber: number;
    exceptionMessage: string;
    exceptionMethodName: string;
    exceptionName: string;
    exceptionRootCauseMessage: string;
    exceptionStackTrace: string;
    exceptionTime: string;
    id: string;
    processStatus: number;
    processTime?: string;
    processUserId?: string;
    requestMethod: string;
    requestParams?: Record<string, unknown>;
    requestUrl: string;
    traceId: string;
    userAgent: string;
    userId?: string;
    userIp: string;
    userType: number;
  }

  /** API 错误日志分页查询 ReqVO */
  export interface ApiErrorLogPageReqVO extends PageParam {
    applicationName?: string;
    exceptionTime?: string[];
    processStatus?: number;
    requestUrl?: string;
    userId?: string;
    userType?: number;
  }
}

/** 获得 API 错误日志分页 */
export async function getApiErrorLogPage(
  params: InfraApiErrorLogApi.ApiErrorLogPageReqVO,
) {
  return requestClient.get<PageResult<InfraApiErrorLogApi.ApiErrorLogRespVO>>(
    '/infra/logger/api-error-log/page',
    {
      params,
      paramsSerializer: 'repeat',
    },
  );
}

/** 更新 API 错误日志的处理状态（query 传参） */
export async function updateApiErrorLogStatus(
  id: string,
  processStatus: number,
) {
  return requestClient.put('/infra/logger/api-error-log/update-status', null, {
    params: { id, processStatus },
  });
}

/** 获取 API 错误日志可导出字段列表 */
export async function getExportApiErrorLogFields() {
  return requestClient.get<ExportField[]>(
    '/infra/logger/api-error-log/export-fields',
  );
}

/** 导出 API 错误日志 */
export async function exportApiErrorLog(
  params: InfraApiErrorLogApi.ApiErrorLogPageReqVO,
) {
  return requestClient.download('/infra/logger/api-error-log/export-excel', {
    params,
    paramsSerializer: 'repeat',
  });
}
