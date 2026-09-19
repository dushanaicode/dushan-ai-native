import type { ExportField, PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 参数配置端点（`/infra/config`）。ID 均为雪花字符串。 */
export namespace InfraConfigDataApi {
  /** 参数配置信息 RespVO */
  export interface ConfigDataRespVO {
    createTime: string;
    description?: string;
    id: string;
    inputProps?: string;
    inputType?: string;
    key: string;
    name: string;
    remark?: string;
    sort: number;
    typeId: string;
    typeName?: string;
    value: string;
    visible: boolean;
  }

  /** 参数配置创建/修改 ReqVO */
  export interface ConfigDataSaveReqVO {
    description?: string;
    id?: string;
    inputProps?: string;
    inputType?: string;
    key: string;
    name: string;
    remark?: string;
    sort?: number;
    typeId: string;
    value: string;
    visible: boolean;
  }

  /** 配置数据分页查询 ReqVO */
  export interface ConfigDataPageReqVO extends PageParam {
    createTime?: string[];
    fields?: string[];
    module?: string;
    name?: string;
    typeId?: string;
  }
}

/** 创建参数配置 */
export async function createConfigData(
  data: InfraConfigDataApi.ConfigDataSaveReqVO,
) {
  return requestClient.post('/infra/config/create', data);
}

/** 修改参数配置 */
export async function updateConfigData(
  data: InfraConfigDataApi.ConfigDataSaveReqVO,
) {
  return requestClient.put('/infra/config/update', data);
}

/** 删除参数配置 */
export async function deleteConfigData(id: string) {
  return requestClient.delete(
    `/infra/config/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 批量删除参数配置 */
export async function deleteConfigDataList(ids: string[]) {
  return requestClient.delete('/infra/config/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}

/** 获得参数配置 */
export async function getConfigData(id: string) {
  return requestClient.get<InfraConfigDataApi.ConfigDataRespVO>(
    `/infra/config/get?id=${encodeURIComponent(id)}`,
  );
}

/** 根据参数键名查询参数值 */
export async function getConfigValueByKey(key: string) {
  return requestClient.get<null | string>('/infra/config/get-value-by-key', {
    params: { key },
  });
}

/** 获取参数配置分页 */
export async function getConfigDataPage(
  params: InfraConfigDataApi.ConfigDataPageReqVO,
) {
  return requestClient.get<PageResult<InfraConfigDataApi.ConfigDataRespVO>>(
    '/infra/config/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 获取参数配置可导出字段列表 */
export async function getExportConfigDataFields() {
  return requestClient.get<ExportField[]>('/infra/config/export-fields');
}

/** 导出参数配置 Excel */
export async function exportConfigData(
  params: InfraConfigDataApi.ConfigDataPageReqVO,
) {
  return requestClient.download('/infra/config/export-excel', {
    params,
    paramsSerializer: 'repeat',
  });
}
