import type { PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 文件配置端点（`/infra/file/config`）。ID 均为雪花字符串。 */
export namespace InfraFileConfigApi {
  /** 文件配置信息 RespVO */
  export interface FileConfigRespVO {
    config: Record<string, unknown>;
    createTime: string;
    id: string;
    master: boolean;
    name: string;
    remark?: string;
    storage: number;
  }

  /** 文件配置创建/修改 ReqVO */
  export interface FileConfigSaveReqVO {
    config: Record<string, unknown>;
    id?: string;
    name: string;
    remark?: string;
    storage: number;
  }

  /** 文件配置分页查询 ReqVO */
  export interface FileConfigPageReqVO extends PageParam {
    createTime?: string[];
    name?: string;
    status?: number;
    storage?: number;
  }

  /** 文件配置精简信息 */
  export interface FileConfigSimpleRespVO {
    id: string;
    master: boolean;
    name: string;
    storage: number;
  }
}

/** 创建文件配置 */
export async function createFileConfig(
  data: InfraFileConfigApi.FileConfigSaveReqVO,
) {
  return requestClient.post('/infra/file/config/create', data);
}

/** 更新文件配置 */
export async function updateFileConfig(
  data: InfraFileConfigApi.FileConfigSaveReqVO,
) {
  return requestClient.put('/infra/file/config/update', data);
}

/** 更新文件配置为 Master */
export async function updateFileConfigMaster(id: string) {
  return requestClient.put('/infra/file/config/update-master', null, {
    params: { id },
  });
}

/** 删除文件配置 */
export async function deleteFileConfig(id: string) {
  return requestClient.delete(
    `/infra/file/config/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 批量删除文件配置 */
export async function deleteFileConfigList(ids: string[]) {
  return requestClient.delete('/infra/file/config/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}

/** 获得文件配置 */
export async function getFileConfig(id: string) {
  return requestClient.get<InfraFileConfigApi.FileConfigRespVO>(
    `/infra/file/config/get?id=${encodeURIComponent(id)}`,
  );
}

/** 获得文件配置分页 */
export async function getFileConfigPage(
  params: InfraFileConfigApi.FileConfigPageReqVO,
) {
  return requestClient.get<PageResult<InfraFileConfigApi.FileConfigRespVO>>(
    '/infra/file/config/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 获取文件配置精简列表 */
export async function getSimpleFileConfigList() {
  return requestClient.get<InfraFileConfigApi.FileConfigSimpleRespVO[]>(
    '/infra/file/config/simple-list',
  );
}

/** 测试文件配置是否正确 */
export async function testFileConfig(id: string) {
  return requestClient.get<string>('/infra/file/config/test', {
    params: { id },
  });
}
