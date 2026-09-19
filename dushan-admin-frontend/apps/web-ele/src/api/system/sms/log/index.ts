import type { ExportField, PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 短信日志端点（`/system/sms/log`）。ID 均为雪花字符串。 */
export namespace SystemSmsLogApi {
  /** 短信日志信息 RespVO */
  export interface SmsLogRespVO {
    apiReceiveCode?: string;
    apiReceiveDataId?: string;
    apiReceiveMsg?: string;
    apiReceiveTime?: string;
    apiRequestId?: string;
    apiSendCode?: string;
    apiSendMsg?: string;
    apiSerialNo?: string;
    apiTemplateId: string;
    channelCode: string;
    channelId: string;
    createTime?: string;
    id: string;
    mobile: string;
    receiveStatus?: number;
    receiveTime?: string;
    sendStatus: number;
    sendTime?: string;
    templateCode: string;
    templateContent: string;
    templateId: string;
    templateParams: Record<string, unknown>;
    templateType: number;
    userId?: string;
    userType?: number;
  }

  /** 短信日志分页查询 ReqVO */
  export interface SmsLogPageReqVO extends PageParam {
    channelId?: string;
    mobile?: string;
    receiveStatus?: number;
    receiveTime?: string[];
    sendStatus?: number;
    sendTime?: string[];
    templateId?: string;
  }
}

/** 获得短信日志分页 */
export async function getSmsLogPage(params: SystemSmsLogApi.SmsLogPageReqVO) {
  return requestClient.get<PageResult<SystemSmsLogApi.SmsLogRespVO>>(
    '/system/sms/log/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 获取短信日志可导出字段列表 */
export async function getExportSmsLogFields() {
  return requestClient.get<ExportField[]>('/system/sms/log/export-fields');
}

/** 导出短信日志 Excel */
export async function exportSmsLog(params: SystemSmsLogApi.SmsLogPageReqVO) {
  return requestClient.download('/system/sms/log/export-excel', {
    params,
    paramsSerializer: 'repeat',
  });
}
