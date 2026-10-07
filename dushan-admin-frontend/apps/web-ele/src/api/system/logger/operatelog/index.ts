import type { ExportField, PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 操作日志端点（`/system/logger/operate-log`）。ID 均为雪花字符串。 */
export namespace SystemOperateLogApi {
  /** 操作日志信息 RespVO */
  export interface OperateLogRespVO {
    action?: string;
    bizId?: string;
    browser: null | string;
    createTime: string;
    extra?: string;
    id: string;
    os: null | string;
    requestMethod: string;
    requestUrl?: string;
    subType?: string;
    traceId?: string;
    type?: string;
    userAgent?: string;
    userId?: string;
    userInfo?: {
      dept_id?: null | string;
      location?: null | string;
      location_status?: string;
      nickname?: string;
      username?: string;
    };
    userIp?: string;
  }

  /** 操作日志分页查询 ReqVO */
  export interface OperateLogPageReqVO extends PageParam {
    action?: string;
    bizId?: string;
    createTime?: string[];
    subType?: string;
    type?: string;
    userId?: string;
  }

  /** 导出查询 ReqVO */
  export interface OperateLogExportReqVO extends OperateLogPageReqVO {
    fields?: string[];
  }
}

/** 获得操作日志分页 */
export async function getOperateLogPage(
  params: SystemOperateLogApi.OperateLogPageReqVO,
) {
  return requestClient.get<PageResult<SystemOperateLogApi.OperateLogRespVO>>(
    '/system/logger/operate-log/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 获取操作日志可导出字段列表 */
export async function getExportOperateLogFields() {
  return requestClient.get<ExportField[]>(
    '/system/logger/operate-log/export-fields',
  );
}

/** 导出操作日志 Excel */
export async function exportOperateLog(
  params: SystemOperateLogApi.OperateLogExportReqVO,
) {
  return requestClient.download('/system/logger/operate-log/export-excel', {
    params,
    paramsSerializer: 'repeat',
  });
}
