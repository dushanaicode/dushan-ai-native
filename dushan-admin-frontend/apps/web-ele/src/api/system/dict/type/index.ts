import type { ExportField, PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 字典类型端点（`/system/dict/type`）。ID 均为雪花字符串。 */
export namespace SystemDictTypeApi {
  /** 字典类型信息 RespVO */
  export interface DictTypeRespVO {
    createTime: string;
    id: string;
    name: string;
    remark?: string;
    status: number;
    type: string;
  }

  /** 字典类型创建/修改 ReqVO */
  export interface DictTypeSaveReqVO {
    id?: string;
    name: string;
    remark?: string;
    status: number;
    type: string;
  }

  /** 字典类型分页查询 ReqVO */
  export interface DictTypePageReqVO extends PageParam {
    createTime?: string[];
    name?: string;
    status?: number;
    type?: string;
  }

  /** 字典类型精简信息 */
  export interface DictTypeSimpleRespVO {
    id: string;
    name: string;
    type: string;
  }
}

/** 获取字典类型精简列表 */
export async function getSimpleDictTypeList() {
  return requestClient.get<SystemDictTypeApi.DictTypeSimpleRespVO[]>(
    '/system/dict/type/simple-list',
  );
}

/** 查询字典类型分页 */
export async function getDictTypePage(
  params: SystemDictTypeApi.DictTypePageReqVO,
) {
  return requestClient.get<PageResult<SystemDictTypeApi.DictTypeRespVO>>(
    '/system/dict/type/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 查询字典类型详情 */
export async function getDictType(id: string) {
  return requestClient.get<SystemDictTypeApi.DictTypeRespVO>(
    `/system/dict/type/get?id=${encodeURIComponent(id)}`,
  );
}

/** 新增字典类型 */
export async function createDictType(
  data: SystemDictTypeApi.DictTypeSaveReqVO,
) {
  return requestClient.post('/system/dict/type/create', data);
}

/** 修改字典类型 */
export async function updateDictType(
  data: SystemDictTypeApi.DictTypeSaveReqVO,
) {
  return requestClient.put('/system/dict/type/update', data);
}

/** 修改字典类型状态 */
export async function updateDictTypeStatus(id: string, status: number) {
  return requestClient.put('/system/dict/type/update-status', { id, status });
}

/** 删除字典类型 */
export async function deleteDictType(id: string) {
  return requestClient.delete(
    `/system/dict/type/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 批量删除字典类型 */
export async function deleteDictTypeList(ids: string[]) {
  return requestClient.delete('/system/dict/type/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}

/** 获取字典类型可导出字段列表 */
export async function getExportDictTypeFields() {
  return requestClient.get<ExportField[]>('/system/dict/type/export-fields');
}

/** 导出字典类型 Excel */
export async function exportDictType(
  params: SystemDictTypeApi.DictTypePageReqVO,
) {
  return requestClient.download('/system/dict/type/export-excel', {
    params,
    paramsSerializer: 'repeat',
  });
}
