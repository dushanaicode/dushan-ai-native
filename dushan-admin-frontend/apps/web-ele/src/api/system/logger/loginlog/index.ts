import type { ExportField, PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 登录日志端点（`/system/logger/login-log`）。ID 均为雪花字符串。 */
export namespace SystemLoginLogApi {
  /** 登录日志信息 RespVO */
  export interface LoginLogRespVO {
    createTime: string;
    id: string;
    logType: number;
    result: number;
    traceId?: string;
    userAgent?: string;
    userId?: string;
    userIp: string;
    username: string;
    userType: number;
  }

  /** 登录日志分页查询 ReqVO */
  export interface LoginLogPageReqVO extends PageParam {
    createTime?: string[];
    logType?: number;
    result?: number;
    userIp?: string;
    username?: string;
  }
}

/** 获得登录日志分页 */
export async function getLoginLogPage(
  params: SystemLoginLogApi.LoginLogPageReqVO,
) {
  return requestClient.get<PageResult<SystemLoginLogApi.LoginLogRespVO>>(
    '/system/logger/login-log/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 获取登录日志可导出字段列表 */
export async function getExportLoginLogFields() {
  return requestClient.get<ExportField[]>(
    '/system/logger/login-log/export-fields',
  );
}

/** 导出登录日志 Excel */
export async function exportLoginLog(
  params: SystemLoginLogApi.LoginLogPageReqVO,
) {
  return requestClient.download('/system/logger/login-log/export-excel', {
    params,
    paramsSerializer: 'repeat',
  });
}
