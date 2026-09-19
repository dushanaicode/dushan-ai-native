import type { ExportField, PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 租户套餐端点（`/system/tenant/package`）。ID 均为雪花字符串。 */
export namespace SystemTenantPackageApi {
  /** AI 模块配额模板配置 */
  export interface TenantPackageAiQuotaConfigVO {
    billingMode?: number;
    dailyTokenLimit?: number;
    enabled?: boolean;
    monthlyAmountLimit?: number;
    monthlyTokenLimit?: number;
  }

  /** 通用配额模板（多模块共享） */
  export interface TenantPackageQuotaConfigVO {
    ai?: TenantPackageAiQuotaConfigVO;
  }

  /** 租户套餐信息 RespVO */
  export interface TenantPackageRespVO {
    createTime: string;
    id: string;
    menuIds: string[];
    name: string;
    quotaConfig?: TenantPackageQuotaConfigVO;
    remark?: string;
    status: number;
  }

  /** 租户套餐创建/修改 ReqVO */
  export interface TenantPackageSaveReqVO {
    id?: string;
    menuIds?: string[];
    name: string;
    quotaConfig?: TenantPackageQuotaConfigVO;
    remark?: string;
    status: number;
  }

  /** 租户套餐分页查询 ReqVO */
  export interface TenantPackagePageReqVO extends PageParam {
    createTime?: string[];
    name?: string;
    status?: number;
  }

  /** 租户套餐精简信息 */
  export interface TenantPackageSimpleRespVO {
    id: string;
    name: string;
  }
}

/** 获得租户套餐分页 */
export async function getTenantPackagePage(
  params: SystemTenantPackageApi.TenantPackagePageReqVO,
) {
  return requestClient.get<
    PageResult<SystemTenantPackageApi.TenantPackageRespVO>
  >('/system/tenant/package/page', {
    params,
    paramsSerializer: 'repeat',
  });
}

/** 获得租户套餐 */
export async function getTenantPackage(id: string) {
  return requestClient.get<SystemTenantPackageApi.TenantPackageRespVO>(
    `/system/tenant/package/get?id=${encodeURIComponent(id)}`,
  );
}

/** 新增租户套餐 */
export async function createTenantPackage(
  data: SystemTenantPackageApi.TenantPackageSaveReqVO,
) {
  return requestClient.post('/system/tenant/package/create', data);
}

/** 修改租户套餐 */
export async function updateTenantPackage(
  data: SystemTenantPackageApi.TenantPackageSaveReqVO,
) {
  return requestClient.put('/system/tenant/package/update', data);
}

/** 修改租户套餐状态 */
export async function updateTenantPackageStatus(id: string, status: number) {
  return requestClient.put('/system/tenant/package/update-status', {
    id,
    status,
  });
}

/** 删除租户套餐 */
export async function deleteTenantPackage(id: string) {
  return requestClient.delete(
    `/system/tenant/package/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 批量删除租户套餐 */
export async function deleteTenantPackageList(ids: string[]) {
  return requestClient.delete('/system/tenant/package/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}

/** 获取租户套餐精简信息列表 */
export async function getSimpleTenantPackageList() {
  return requestClient.get<SystemTenantPackageApi.TenantPackageSimpleRespVO[]>(
    '/system/tenant/package/simple-list',
  );
}

/** 获取租户套餐可导出字段列表 */
export async function getExportTenantPackageFields() {
  return requestClient.get<ExportField[]>(
    '/system/tenant/package/export-fields',
  );
}

/** 导出租户套餐 Excel */
export async function exportTenantPackage(
  params: SystemTenantPackageApi.TenantPackagePageReqVO,
) {
  return requestClient.download('/system/tenant/package/export-excel', {
    params,
    paramsSerializer: 'repeat',
  });
}
