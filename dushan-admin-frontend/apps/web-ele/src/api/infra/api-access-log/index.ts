import type { ExportField, PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** API 访问日志端点（`/infra/logger/api-access-log`）。ID 均为雪花字符串。 */
export namespace InfraApiAccessLogApi {
  /** API 访问日志信息 RespVO */
  export interface ApiAccessLogRespVO {
    applicationName: string;
    beginTime: string;
    createTime: string;
    duration: number;
    endTime: string;
    id: string;
    operateModule: string;
    operateName: string;
    operateType: number;
    requestMethod: string;
    requestParams?: Record<string, unknown>;
    requestUrl: string;
    responseBody?: unknown;
    resultCode: number;
    resultMsg?: string;
    traceId: string;
    userAgent: string;
    userId?: string;
    userIp: string;
    userType: number;
  }

  /** API 访问日志分页查询 ReqVO */
  export interface ApiAccessLogPageReqVO extends PageParam {
    applicationName?: string;
    beginTime?: string[];
    duration?: number;
    requestUrl?: string;
    resultCode?: number;
    userId?: string;
    userType?: number;
  }
}

/** 获得 API 访问日志分页 */
export async function getApiAccessLogPage(
  params: InfraApiAccessLogApi.ApiAccessLogPageReqVO,
) {
  return requestClient.get<PageResult<InfraApiAccessLogApi.ApiAccessLogRespVO>>(
    '/infra/logger/api-access-log/page',
    {
      params,
      paramsSerializer: 'repeat',
    },
  );
}

/** 获取 API 访问日志可导出字段列表 */
export async function getExportApiAccessLogFields() {
  return requestClient.get<ExportField[]>(
    '/infra/logger/api-access-log/export-fields',
  );
}

/** 导出 API 访问日志 */
export async function exportApiAccessLog(
  params: InfraApiAccessLogApi.ApiAccessLogPageReqVO,
) {
  return requestClient.download('/infra/logger/api-access-log/export-excel', {
    params,
    paramsSerializer: 'repeat',
  });
}
