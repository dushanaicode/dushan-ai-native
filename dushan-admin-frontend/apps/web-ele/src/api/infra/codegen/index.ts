import type { PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 代码生成端点（`/infra/codegen`）。ID 均为雪花字符串。 */
export namespace InfraCodegenApi {
  /** 代码生成表 RespVO */
  export interface CodegenTableRespVO {
    author?: null | string;
    businessName: string;
    classComment: string;
    className: string;
    createTime?: null | string;
    dataSourceConfigId: string;
    enableExport: boolean;
    frontType: number;
    id: string;
    masterTableId?: null | string;
    moduleName: string;
    parentMenuId?: null | string;
    remark?: null | string;
    scene: number;
    subJoinColumnId?: null | string;
    subJoinMany?: boolean | null;
    tableComment: string;
    tableName: string;
    templateType: number;
    treeNameColumnId?: null | string;
    treeParentColumnId?: null | string;
    updateTime?: null | string;
  }

  /** 代码生成表更新 ReqVO */
  export interface CodegenTableUpdateReqVO extends CodegenTableRespVO {
    dataSourceConfigId: string;
  }

  /** 代码生成列 RespVO */
  export interface CodegenColumnRespVO {
    columnComment: string;
    columnName: string;
    createOperation: boolean;
    dataType: string;
    dictType?: null | string;
    example?: null | string;
    fieldName: string;
    fieldType: string;
    htmlType: string;
    id: string;
    listOperation: boolean;
    listOperationCondition: string;
    listOperationResult: boolean;
    nullable: boolean;
    orderNo: number;
    primaryKey: boolean;
    tableId: string;
    updateOperation: boolean;
  }

  /** 代码生成列更新 ReqVO（结构与 Resp 一致） */
  export type CodegenColumnUpdateReqVO = CodegenColumnRespVO;

  /** 代码生成更新请求 VO（表 + 列） */
  export interface CodegenUpdateReqVO {
    columns: CodegenColumnUpdateReqVO[];
    table: CodegenTableUpdateReqVO;
  }

  /** 代码生成详情 RespVO（表 + 列） */
  export interface CodegenDetailRespVO {
    columns: CodegenColumnRespVO[];
    table: CodegenTableRespVO;
  }

  /** 代码生成表分页查询 ReqVO */
  export interface CodegenTablePageReqVO extends PageParam {
    createTime?: string[];
    tableComment?: string;
    tableName?: string;
  }

  /** 数据库表信息（导入表时展示） */
  export interface DatabaseTableRespVO {
    comment?: string;
    name: string;
  }

  /** 批量导入 ReqVO */
  export interface CodegenCreateListReqVO {
    dataSourceConfigId: string;
    tableNames: string[];
  }

  /** 代码预览 RespVO */
  export interface CodegenPreviewRespVO {
    code: string;
    filePath: string;
  }
}

/** 批量导入数据库表 */
export async function createCodegenList(
  data: InfraCodegenApi.CodegenCreateListReqVO,
) {
  return requestClient.post<string[]>('/infra/codegen/create-list', data);
}

/** 更新代码生成配置 */
export async function updateCodegen(data: InfraCodegenApi.CodegenUpdateReqVO) {
  return requestClient.put('/infra/codegen/update', data);
}

/** 删除代码生成表 */
export async function deleteCodegen(id: string) {
  return requestClient.delete(
    `/infra/codegen/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 批量删除代码生成表 */
export async function deleteCodegenList(ids: string[]) {
  return requestClient.delete('/infra/codegen/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}

/** 获得代码生成表分页 */
export async function getCodegenTablePage(
  params: InfraCodegenApi.CodegenTablePageReqVO,
) {
  return requestClient.get<PageResult<InfraCodegenApi.CodegenTableRespVO>>(
    '/infra/codegen/table/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 获得代码生成详情 */
export async function getCodegenDetail(tableId: string) {
  return requestClient.get<InfraCodegenApi.CodegenDetailRespVO>(
    `/infra/codegen/detail?id=${encodeURIComponent(tableId)}`,
  );
}

/** 获得代码生成表列表 */
export async function getCodegenTableList(params: {
  dataSourceConfigId: string;
}) {
  return requestClient.get<InfraCodegenApi.CodegenTableRespVO[]>(
    '/infra/codegen/table/list',
    { params },
  );
}

/** 获取数据库的表列表 */
export async function getSchemaTableList(params: {
  dataSourceConfigId: string;
  tableComment?: string;
  tableName?: string;
}) {
  return requestClient.get<InfraCodegenApi.DatabaseTableRespVO[]>(
    '/infra/codegen/db/table/list',
    { params },
  );
}

/** 从数据库同步表结构 */
export async function syncCodegenFromDb(tableId: string) {
  return requestClient.put('/infra/codegen/sync-from-db', null, {
    params: { tableId },
  });
}

/** 预览代码 */
export async function previewCodegen(tableId: string) {
  return requestClient.get<InfraCodegenApi.CodegenPreviewRespVO[]>(
    '/infra/codegen/preview',
    { params: { tableId } },
  );
}

/** 下载代码 */
export async function downloadCodegen(tableId: string) {
  return requestClient.download('/infra/codegen/download', {
    params: { tableId },
  });
}
