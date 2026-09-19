import type { ExportField, PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 数据源配置端点（`/infra/data-source`）。ID 均为雪花字符串。 */
export namespace InfraDataSourceConfigApi {
  /** 数据源配置信息 RespVO（url 敏感不出参） */
  export interface DataSourceConfigRespVO {
    createTime: string;
    dbType: string;
    echo: boolean;
    id: string;
    isDefault: boolean;
    maxOverflow: number;
    name: string;
    poolRecycle: number;
    poolSize: number;
    poolTimeout: number;
    remark?: string;
    sourceType: number;
    status: number;
  }

  /** 数据源配置创建/修改 ReqVO */
  export interface DataSourceConfigSaveReqVO {
    dbType: string;
    echo?: boolean;
    id?: string;
    isDefault?: boolean;
    maxOverflow?: number;
    name: string;
    poolRecycle?: number;
    poolSize?: number;
    poolTimeout?: number;
    remark?: string;
    sourceType: number;
    status: number;
    url?: string;
  }

  /** 数据源配置分页查询 ReqVO */
  export interface DataSourceConfigPageReqVO extends PageParam {
    createTime?: string[];
    dbType?: string;
    name?: string;
    sourceType?: number;
    status?: number;
  }

  /** 数据源配置精简信息 */
  export interface DataSourceConfigSimpleRespVO {
    dbType: string;
    id: string;
    name: string;
    sourceType: number;
  }

  /** 数据源配置连接测试 RespVO */
  export interface DataSourceConfigTestRespVO {
    message: string;
    success: boolean;
  }
}

/** 创建数据源配置 */
export async function createDataSourceConfig(
  data: InfraDataSourceConfigApi.DataSourceConfigSaveReqVO,
) {
  return requestClient.post('/infra/data-source/create', data);
}

/** 更新数据源配置 */
export async function updateDataSourceConfig(
  data: InfraDataSourceConfigApi.DataSourceConfigSaveReqVO,
) {
  return requestClient.put('/infra/data-source/update', data);
}

/** 修改数据源配置状态 */
export async function updateDataSourceConfigStatus(id: string, status: number) {
  return requestClient.put('/infra/data-source/update-status', {
    id,
    status,
  });
}

/** 删除数据源配置 */
export async function deleteDataSourceConfig(id: string) {
  return requestClient.delete(
    `/infra/data-source/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 获得数据源配置 */
export async function getDataSourceConfig(id: string) {
  return requestClient.get<InfraDataSourceConfigApi.DataSourceConfigRespVO>(
    `/infra/data-source/get?id=${encodeURIComponent(id)}`,
  );
}

/** 获得数据源配置列表 */
export async function getDataSourceConfigList() {
  return requestClient.get<InfraDataSourceConfigApi.DataSourceConfigRespVO[]>(
    '/infra/data-source/list',
  );
}

/** 获得数据源配置分页 */
export async function getDataSourceConfigPage(
  params: InfraDataSourceConfigApi.DataSourceConfigPageReqVO,
) {
  return requestClient.get<
    PageResult<InfraDataSourceConfigApi.DataSourceConfigRespVO>
  >('/infra/data-source/page', { params, paramsSerializer: 'repeat' });
}

/** 根据状态获得数据源配置精简列表 */
export async function getDataSourceConfigListByStatus(status: number) {
  return requestClient.get<
    InfraDataSourceConfigApi.DataSourceConfigSimpleRespVO[]
  >('/infra/data-source/list-by-status', { params: { status } });
}

/** 测试数据源配置 */
export async function testDataSourceConfig(id: string) {
  return requestClient.post<InfraDataSourceConfigApi.DataSourceConfigTestRespVO>(
    '/infra/data-source/test',
    null,
    { params: { id } },
  );
}

/** 获取数据源配置可导出字段列表 */
export async function getExportDataSourceConfigFields() {
  return requestClient.get<ExportField[]>('/infra/data-source/export-fields');
}

/** 导出数据源配置 */
export async function exportDataSourceConfig(
  params: InfraDataSourceConfigApi.DataSourceConfigPageReqVO,
) {
  return requestClient.download('/infra/data-source/export-excel', {
    params,
    paramsSerializer: 'repeat',
  });
}
