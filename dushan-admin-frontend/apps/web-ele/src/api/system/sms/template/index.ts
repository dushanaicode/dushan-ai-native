import type { ExportField, PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 短信模板端点（`/system/sms/template`）。ID 均为雪花字符串。 */
export namespace SystemSmsTemplateApi {
  /** 短信模板信息 RespVO */
  export interface SmsTemplateRespVO {
    apiTemplateId?: string;
    builtin?: number;
    channelCode?: string;
    channelId?: string;
    code?: string;
    content?: string;
    createTime?: string;
    id?: string;
    name?: string;
    params?: string[];
    remark?: string;
    status?: number;
    type?: number;
  }

  /** 短信模板创建/修改 ReqVO */
  export interface SmsTemplateSaveReqVO {
    apiTemplateId: string;
    channelId: string;
    code: string;
    content: string;
    id?: string;
    name: string;
    remark?: string;
    status: number;
    type: number;
  }

  /** 短信模板分页查询 ReqVO */
  export interface SmsTemplatePageReqVO extends PageParam {
    channelId?: string;
    code?: string;
    content?: string;
    createTime?: string[];
    status?: number;
    type?: number;
  }

  /** 短信发送 ReqVO */
  export interface SmsTemplateSendReqVO {
    mobile: string;
    templateCode: string;
    templateParams?: Record<string, unknown>;
  }

  /** 短信模板精简信息 */
  export interface SmsTemplateSimpleRespVO {
    code: string;
    id: string;
    name: string;
  }
}

/** 创建短信模板 */
export async function createSmsTemplate(
  data: SystemSmsTemplateApi.SmsTemplateSaveReqVO,
) {
  return requestClient.post('/system/sms/template/create', data);
}

/** 更新短信模板 */
export async function updateSmsTemplate(
  data: SystemSmsTemplateApi.SmsTemplateSaveReqVO,
) {
  return requestClient.put('/system/sms/template/update', data);
}

/** 修改短信模板状态 */
export async function updateSmsTemplateStatus(id: string, status: number) {
  return requestClient.put('/system/sms/template/update-status', {
    id,
    status,
  });
}

/** 删除短信模板 */
export async function deleteSmsTemplate(id: string) {
  return requestClient.delete(
    `/system/sms/template/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 批量删除短信模板 */
export async function deleteSmsTemplateList(ids: string[]) {
  return requestClient.delete('/system/sms/template/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}

/** 获得短信模板 */
export async function getSmsTemplate(id: string) {
  return requestClient.get<SystemSmsTemplateApi.SmsTemplateRespVO>(
    `/system/sms/template/get?id=${encodeURIComponent(id)}`,
  );
}

/** 获得短信模板分页 */
export async function getSmsTemplatePage(
  params: SystemSmsTemplateApi.SmsTemplatePageReqVO,
) {
  return requestClient.get<PageResult<SystemSmsTemplateApi.SmsTemplateRespVO>>(
    '/system/sms/template/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 获取短信模板可导出字段列表 */
export async function getExportSmsTemplateFields() {
  return requestClient.get<ExportField[]>('/system/sms/template/export-fields');
}

/** 导出短信模板 Excel */
export async function exportSmsTemplate(
  params: SystemSmsTemplateApi.SmsTemplatePageReqVO,
) {
  return requestClient.download('/system/sms/template/export-excel', {
    params,
    paramsSerializer: 'repeat',
  });
}

/** 获得短信模板精简列表 */
export async function getSimpleSmsTemplateList() {
  return requestClient.get<SystemSmsTemplateApi.SmsTemplateSimpleRespVO[]>(
    '/system/sms/template/simple-list',
  );
}

/** 发送短信 */
export async function sendSms(data: SystemSmsTemplateApi.SmsTemplateSendReqVO) {
  return requestClient.post('/system/sms/template/send-sms', data);
}
