import type { ExportField, PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 邮箱日志端点（`/system/mail/log`）。ID 均为雪花字符串。 */
export namespace SystemMailLogApi {
  /** 邮件日志信息 RespVO */
  export interface MailLogRespVO {
    accountId: string;
    bccMail?: string;
    ccMail?: string;
    createTime: string;
    fromMail: string;
    id: string;
    sendException?: string;
    sendMessageId?: string;
    sendStatus: number;
    sendTime?: string;
    templateCode: string;
    templateContent: string;
    templateId: string;
    templateNickname?: string;
    templateParams: Record<string, unknown>;
    templateTitle: string;
    toMail: string;
    userId?: string;
    userType?: number;
  }

  /** 邮件日志分页查询 ReqVO */
  export interface MailLogPageReqVO extends PageParam {
    accountId?: string;
    accountUsername?: string;
    fromMail?: string;
    sendStatus?: number;
    sendTimeBegin?: string;
    sendTimeEnd?: string;
    templateCode?: string;
    templateId?: string;
    templateNickname?: string;
    templateTitle?: string;
    toMail?: string;
    userId?: string;
    userType?: number;
  }
}

/** 获得邮箱日志分页 */
export async function getMailLogPage(
  params: SystemMailLogApi.MailLogPageReqVO,
) {
  return requestClient.get<PageResult<SystemMailLogApi.MailLogRespVO>>(
    '/system/mail/log/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 获得邮箱日志 */
export async function getMailLog(id: string) {
  return requestClient.get<SystemMailLogApi.MailLogRespVO>(
    `/system/mail/log/get?id=${encodeURIComponent(id)}`,
  );
}

/** 获取邮箱日志可导出字段列表 */
export async function getExportMailLogFields() {
  return requestClient.get<ExportField[]>('/system/mail/log/export-fields');
}

/** 导出邮箱日志 Excel */
export async function exportMailLog(params: SystemMailLogApi.MailLogPageReqVO) {
  return requestClient.download('/system/mail/log/export-excel', {
    params,
    paramsSerializer: 'repeat',
  });
}
