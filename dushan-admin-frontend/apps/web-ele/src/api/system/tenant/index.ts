import type { ExportField, PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 租户端点（`/system/tenant`）。ID 均为雪花字符串。 */
export namespace SystemTenantApi {
  /** 租户信息 RespVO */
  export interface TenantRespVO {
    accountCount: number;
    contactMobile?: string;
    contactName: string;
    createTime: string;
    expireTime: string;
    id: string;
    name: string;
    packageId: string;
    status: number;
    websites?: string[];
  }

  /** 租户创建 ReqVO（含管理员账号） */
  export interface TenantSaveReqVO {
    accountCount: number;
    contactMobile?: string;
    contactName: string;
    expireTime: string;
    id?: string;
    name: string;
    packageId: string;
    password: string;
    status: number;
    username: string;
    websites?: string[];
  }

  /** 租户更新 ReqVO（不含账号字段，全部可选） */
  export interface TenantUpdateReqVO {
    accountCount?: number;
    contactMobile?: string;
    contactName?: string;
    expireTime?: string;
    id: string;
    name?: string;
    packageId?: string;
    status?: number;
    websites?: string[];
  }

  /** 租户分页查询 ReqVO */
  export interface TenantPageReqVO extends PageParam {
    contactMobile?: string;
    contactName?: string;
    createTime?: string[];
    name?: string;
    status?: number;
  }

  /** 租户精简信息 */
  export interface TenantSimpleRespVO {
    id: string;
    name: string;
  }
}

/** 使用租户名获得租户编号 */
export async function getTenantIdByName(name: string) {
  return requestClient.get<string>('/system/tenant/get-id-by-name', {
    params: { name },
  });
}

/** 获取租户精简信息列表 */
export async function getTenantSimpleList() {
  return requestClient.get<SystemTenantApi.TenantSimpleRespVO[]>(
    '/system/tenant/simple-list',
  );
}

/** 使用网站获取租户 */
export async function getTenantByWebsite(website: string) {
  return requestClient.get<SystemTenantApi.TenantRespVO>(
    '/system/tenant/get-by-website',
    { params: { website } },
  );
}

/** 查询租户分页 */
export async function getTenantPage(params: SystemTenantApi.TenantPageReqVO) {
  return requestClient.get<PageResult<SystemTenantApi.TenantRespVO>>(
    '/system/tenant/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 查询租户详情 */
export async function getTenant(id: string) {
  return requestClient.get<SystemTenantApi.TenantRespVO>(
    `/system/tenant/get?id=${encodeURIComponent(id)}`,
  );
}

/** 新增租户 */
export async function createTenant(data: SystemTenantApi.TenantSaveReqVO) {
  return requestClient.post('/system/tenant/create', data);
}

/** 修改租户 */
export async function updateTenant(data: SystemTenantApi.TenantUpdateReqVO) {
  return requestClient.put('/system/tenant/update', data);
}

/** 修改租户状态 */
export async function updateTenantStatus(id: string, status: number) {
  return requestClient.put('/system/tenant/update-status', { id, status });
}

/** 删除租户 */
export async function deleteTenant(id: string) {
  return requestClient.delete(
    `/system/tenant/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 批量删除租户 */
export async function deleteTenantList(ids: string[]) {
  return requestClient.delete('/system/tenant/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}

/** 获取租户可导出字段列表 */
export async function getExportTenantFields() {
  return requestClient.get<ExportField[]>('/system/tenant/export-fields');
}

/** 导出租户 Excel */
export async function exportTenant(params: SystemTenantApi.TenantPageReqVO) {
  return requestClient.download('/system/tenant/export-excel', {
    params,
    paramsSerializer: 'repeat',
  });
}
