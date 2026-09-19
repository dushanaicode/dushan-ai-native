import type { ExportField, PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 配置类型端点（`/infra/config/type`）。ID 均为雪花字符串。 */
export namespace InfraConfigTypeApi {
  /** 配置类型信息 RespVO */
  export interface ConfigTypeRespVO {
    code: string;
    createTime: string;
    id?: string;
    module: string;
    name: string;
    remark?: string;
    status: number;
  }

  /** 配置类型创建/修改 ReqVO */
  export interface ConfigTypeSaveReqVO {
    code: string;
    id?: string;
    module?: string;
    name: string;
    remark?: string;
    status: number;
  }

  /** 配置类型分页查询 ReqVO */
  export interface ConfigTypePageReqVO extends PageParam {
    code?: string;
    createTime?: string[];
    fields?: string[];
    module?: string;
    name?: string;
    status?: number;
  }

  /** 配置类型精简信息 */
  export interface ConfigTypeSimpleRespVO {
    code: string;
    id?: string;
    module: string;
    name: string;
  }
}

/** 创建配置类型 */
export async function createConfigType(
  data: InfraConfigTypeApi.ConfigTypeSaveReqVO,
) {
  return requestClient.post('/infra/config/type/create', data);
}

/** 修改配置类型 */
export async function updateConfigType(
  data: InfraConfigTypeApi.ConfigTypeSaveReqVO,
) {
  return requestClient.put('/infra/config/type/update', data);
}

/** 修改配置类型状态 */
export async function updateConfigTypeStatus(id: string, status: number) {
  return requestClient.put('/infra/config/type/update-status', {
    id,
    status,
  });
}

/** 删除配置类型 */
export async function deleteConfigType(id: string) {
  return requestClient.delete(
    `/infra/config/type/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 批量删除配置类型 */
export async function deleteConfigTypeList(ids: string[]) {
  return requestClient.delete('/infra/config/type/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}

/** 获得配置类型分页列表 */
export async function getConfigTypePage(
  params: InfraConfigTypeApi.ConfigTypePageReqVO,
) {
  return requestClient.get<PageResult<InfraConfigTypeApi.ConfigTypeRespVO>>(
    '/infra/config/type/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 查询配置类型详细 */
export async function getConfigType(id: string) {
  return requestClient.get<InfraConfigTypeApi.ConfigTypeRespVO>(
    `/infra/config/type/get?id=${encodeURIComponent(id)}`,
  );
}

/** 获得全部配置类型精简列表 */
export async function getSimpleConfigTypeList(module?: string) {
  return requestClient.get<InfraConfigTypeApi.ConfigTypeSimpleRespVO[]>(
    '/infra/config/type/list-all-simple',
    { params: module === undefined ? {} : { module } },
  );
}

/** 获取配置类型可导出字段列表 */
export async function getExportConfigTypeFields() {
  return requestClient.get<ExportField[]>('/infra/config/type/export-fields');
}

/** 导出配置类型 Excel */
export async function exportConfigType(
  params: InfraConfigTypeApi.ConfigTypePageReqVO,
) {
  return requestClient.download('/infra/config/type/export-excel', {
    params,
    paramsSerializer: 'repeat',
  });
}
