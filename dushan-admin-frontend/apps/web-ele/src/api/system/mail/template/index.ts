import type { ExportField, PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 邮件模版端点（`/system/mail/template`）。ID 均为雪花字符串。 */
export namespace SystemMailTemplateApi {
  /** 邮件模版信息 RespVO */
  export interface MailTemplateRespVO {
    accountId: string;
    code: string;
    content: string;
    createTime: string;
    id: string;
    name: string;
    nickname: string;
    params?: string[];
    remark?: string;
    status: number;
    title: string;
  }

  /** 邮件模版创建/修改 ReqVO */
  export interface MailTemplateSaveReqVO {
    accountId: string;
    code: string;
    content: string;
    id?: string;
    name: string;
    nickname: string;
    params?: string[];
    remark?: string;
    status: number;
    title: string;
  }

  /** 邮件模版分页查询 ReqVO */
  export interface MailTemplatePageReqVO extends PageParam {
    accountId?: string;
    code?: string;
    createTime?: string[];
    name?: string;
    status?: number;
  }

  /** 邮件发送 ReqVO */
  export interface MailTemplateSendReqVO {
    bccMails?: string[];
    ccMails?: string[];
    templateCode: string;
    templateParams?: Record<string, unknown>;
    toMails: string[];
  }

  /** 邮件模版精简信息 */
  export interface MailTemplateSimpleRespVO {
    id: string;
    name: string;
  }
}

/** 创建邮件模版 */
export async function createMailTemplate(
  data: SystemMailTemplateApi.MailTemplateSaveReqVO,
) {
  return requestClient.post('/system/mail/template/create', data);
}

/** 修改邮件模版 */
export async function updateMailTemplate(
  data: SystemMailTemplateApi.MailTemplateSaveReqVO,
) {
  return requestClient.put('/system/mail/template/update', data);
}

/** 修改邮件模板状态 */
export async function updateMailTemplateStatus(id: string, status: number) {
  return requestClient.put('/system/mail/template/update-status', {
    id,
    status,
  });
}

/** 删除邮件模版 */
export async function deleteMailTemplate(id: string) {
  return requestClient.delete(
    `/system/mail/template/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 批量删除邮件模板 */
export async function deleteMailTemplateList(ids: string[]) {
  return requestClient.delete('/system/mail/template/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}

/** 获得邮件模版 */
export async function getMailTemplate(id: string) {
  return requestClient.get<SystemMailTemplateApi.MailTemplateRespVO>(
    `/system/mail/template/get?id=${encodeURIComponent(id)}`,
  );
}

/** 获得邮件模版分页 */
export async function getMailTemplatePage(
  params: SystemMailTemplateApi.MailTemplatePageReqVO,
) {
  return requestClient.get<
    PageResult<SystemMailTemplateApi.MailTemplateRespVO>
  >('/system/mail/template/page', { params, paramsSerializer: 'repeat' });
}

/** 获取邮件模版可导出字段列表 */
export async function getExportMailTemplateFields() {
  return requestClient.get<ExportField[]>(
    '/system/mail/template/export-fields',
  );
}

/** 导出邮件模版 Excel */
export async function exportMailTemplate(
  params: SystemMailTemplateApi.MailTemplatePageReqVO,
) {
  return requestClient.download('/system/mail/template/export-excel', {
    params,
    paramsSerializer: 'repeat',
  });
}

/** 获得邮件模版精简列表 */
export async function getSimpleMailTemplateList() {
  return requestClient.get<SystemMailTemplateApi.MailTemplateSimpleRespVO[]>(
    '/system/mail/template/simple-list',
  );
}

/** 发送邮件 */
export async function sendMail(
  data: SystemMailTemplateApi.MailTemplateSendReqVO,
) {
  return requestClient.post('/system/mail/template/send-mail', data);
}
