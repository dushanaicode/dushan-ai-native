import type { ExportField, PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 邮箱账号端点（`/system/mail/account`）。ID 均为雪花字符串。 */
export namespace SystemMailAccountApi {
  /** 邮箱账号信息 RespVO */
  export interface MailAccountRespVO {
    createTime: string;
    host: string;
    id: string;
    mail: string;
    password: string;
    port: number;
    sslEnable: boolean;
    starttlsEnable: boolean;
    username: string;
  }

  /** 邮箱账号创建/修改 ReqVO */
  export interface MailAccountSaveReqVO {
    host: string;
    id?: string;
    mail: string;
    password: string;
    port: number;
    sslEnable: boolean;
    starttlsEnable: boolean;
    username: string;
  }

  /** 邮箱账号分页查询 ReqVO */
  export interface MailAccountPageReqVO extends PageParam {
    mail?: string;
    username?: string;
  }

  /** 邮箱账号精简信息 */
  export interface MailAccountSimpleRespVO {
    id: string;
    mail: string;
  }
}

/** 创建邮箱账号 */
export async function createMailAccount(
  data: SystemMailAccountApi.MailAccountSaveReqVO,
) {
  return requestClient.post('/system/mail/account/create', data);
}

/** 修改邮箱账号 */
export async function updateMailAccount(
  data: SystemMailAccountApi.MailAccountSaveReqVO,
) {
  return requestClient.put('/system/mail/account/update', data);
}

/** 删除邮箱账号 */
export async function deleteMailAccount(id: string) {
  return requestClient.delete(
    `/system/mail/account/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 批量删除邮箱账号 */
export async function deleteMailAccountList(ids: string[]) {
  return requestClient.delete('/system/mail/account/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}

/** 获得邮箱账号 */
export async function getMailAccount(id: string) {
  return requestClient.get<SystemMailAccountApi.MailAccountRespVO>(
    `/system/mail/account/get?id=${encodeURIComponent(id)}`,
  );
}

/** 获得邮箱账号分页 */
export async function getMailAccountPage(
  params: SystemMailAccountApi.MailAccountPageReqVO,
) {
  return requestClient.get<PageResult<SystemMailAccountApi.MailAccountRespVO>>(
    '/system/mail/account/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 获取邮箱账号可导出字段列表 */
export async function getExportMailAccountFields() {
  return requestClient.get<ExportField[]>('/system/mail/account/export-fields');
}

/** 导出邮箱账号 Excel */
export async function exportMailAccount(
  params: SystemMailAccountApi.MailAccountPageReqVO,
) {
  return requestClient.download('/system/mail/account/export-excel', {
    params,
    paramsSerializer: 'repeat',
  });
}

/** 获得邮箱账号精简列表 */
export async function getSimpleMailAccountList() {
  return requestClient.get<SystemMailAccountApi.MailAccountSimpleRespVO[]>(
    '/system/mail/account/simple-list',
  );
}
