import type { ExportField, PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 字典数据端点（`/system/dict/data`）。ID 均为雪花字符串。 */
export namespace SystemDictDataApi {
  /** 字典数据信息 RespVO */
  export interface DictDataRespVO {
    colorType?: string;
    createTime: string;
    dictType: string;
    id: string;
    label: string;
    permission?: string;
    remark?: string;
    sort: number;
    status: number;
    tagStyle?: Record<string, unknown>;
    value: string;
  }

  /** 字典数据创建/修改 ReqVO */
  export interface DictDataSaveReqVO {
    colorType?: string;
    dictType: string;
    id?: string;
    label: string;
    permission?: string;
    remark?: string;
    sort: number;
    status: number;
    tagStyle?: Record<string, unknown>;
    value: string;
  }

  /** 字典数据分页查询 ReqVO */
  export interface DictDataPageReqVO extends PageParam {
    createTime?: string[];
    dictType?: string;
    label?: string;
    status?: number;
  }

  /** 字典数据精简信息（/simple-list，前端字典运行时消费） */
  export interface DictDataSimpleRespVO {
    colorType?: string;
    dictType: string;
    label: string;
    permission?: string;
    tagStyle?: Record<string, unknown>;
    value: string;
  }
}

/** 查询字典数据分页 */
export async function getDictDataPage(
  params: SystemDictDataApi.DictDataPageReqVO,
) {
  return requestClient.get<PageResult<SystemDictDataApi.DictDataRespVO>>(
    '/system/dict/data/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 查询字典数据详情 */
export async function getDictData(id: string) {
  return requestClient.get<SystemDictDataApi.DictDataRespVO>(
    `/system/dict/data/get?id=${encodeURIComponent(id)}`,
  );
}

/** 新增字典数据 */
export async function createDictData(
  data: SystemDictDataApi.DictDataSaveReqVO,
) {
  return requestClient.post('/system/dict/data/create', data);
}

/** 修改字典数据 */
export async function updateDictData(
  data: SystemDictDataApi.DictDataSaveReqVO,
) {
  return requestClient.put('/system/dict/data/update', data);
}

/** 修改字典数据状态 */
export async function updateDictDataStatus(id: string, status: number) {
  return requestClient.put('/system/dict/data/update-status', { id, status });
}

/** 删除字典数据 */
export async function deleteDictData(id: string) {
  return requestClient.delete(
    `/system/dict/data/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 批量删除字典数据 */
export async function deleteDictDataList(ids: string[]) {
  return requestClient.delete('/system/dict/data/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}

/** 获取字典数据可导出字段列表 */
export async function getExportDictDataFields() {
  return requestClient.get<ExportField[]>('/system/dict/data/export-fields');
}

/** 导出字典数据 Excel */
export async function exportDictData(
  params: SystemDictDataApi.DictDataPageReqVO,
) {
  return requestClient.download('/system/dict/data/export-excel', {
    params,
    paramsSerializer: 'repeat',
  });
}
