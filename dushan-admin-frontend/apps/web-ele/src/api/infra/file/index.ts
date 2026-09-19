import type { PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 文件端点（`/infra/file`）。ID 均为雪花字符串。 */
export namespace InfraFileApi {
  /** 文件信息 RespVO */
  export interface FileRespVO {
    configId: string;
    createTime: string;
    id: string;
    name: string;
    path: string;
    size: number;
    type?: string;
    url: string;
  }

  /** 文件分页查询 ReqVO */
  export interface FilePageReqVO extends PageParam {
    configId?: string;
    createTime?: string[];
    path?: string;
    type?: string;
  }

  /** 文件预签名地址 RespVO */
  export interface FilePresignedUrlRespVO {
    configId: string;
    path: string;
    uploadUrl: string;
    url: string;
  }

  /** 文件创建 ReqVO（配合预签名直传） */
  export interface FileCreateReqVO {
    configId: string;
    name: string;
    path: string;
    size: number;
    type?: string;
    url: string;
  }

  /** 文件/目录对象信息 */
  export interface FileObjectVO {
    isDirectory?: boolean;
    key: string;
    lastModified?: string;
    name: string;
    size?: number;
    type?: string;
    url?: string;
  }

  /** 列举对象响应 VO */
  export interface FileListObjectsRespVO {
    currentPrefix?: string;
    isTruncated?: boolean;
    nextMarker?: string;
    objects: FileObjectVO[];
  }

  /** 新建目录 ReqVO */
  export interface FileCreateDirectoryReqVO {
    configId: string;
    directoryPath: string;
  }

  /** 重命名 ReqVO */
  export interface FileRenameReqVO {
    configId: string;
    newName: string;
    oldKey: string;
  }

  /** 搜索 ReqVO */
  export interface FileSearchReqVO extends PageParam {
    configId: string;
    keyword?: string;
    prefix?: string;
    searchMode?: 'fuzzy' | 'prefix';
  }
}

/** 上传文件（后端中转） */
export async function uploadFile(
  file: File,
  directory?: string,
  configId?: string,
) {
  const formData = new FormData();
  formData.append('file', file);
  if (directory !== undefined) {
    formData.append('directory', directory);
  }
  if (configId !== undefined) {
    formData.append('configId', configId);
  }
  return requestClient.post<string>('/infra/file/upload', formData);
}

/** 获取文件预签名地址 */
export async function getFilePresignedUrl(name: string, directory?: string) {
  return requestClient.get<InfraFileApi.FilePresignedUrlRespVO>(
    '/infra/file/presigned-url',
    { params: { directory, name } },
  );
}

/** 创建文件记录（配合预签名直传） */
export async function createFileRecord(data: InfraFileApi.FileCreateReqVO) {
  return requestClient.post<string>('/infra/file/create', data);
}

/** 获得文件分页 */
export async function getFilePage(params: InfraFileApi.FilePageReqVO) {
  return requestClient.get<PageResult<InfraFileApi.FileRespVO>>(
    '/infra/file/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 列举目录内容 */
export async function listObjects(params: {
  configId: string;
  delimiter?: string;
  prefix?: string;
}) {
  return requestClient.get<InfraFileApi.FileListObjectsRespVO>(
    '/infra/file/list-objects',
    { params },
  );
}

/** 新建文件夹 */
export async function createDirectory(
  data: InfraFileApi.FileCreateDirectoryReqVO,
) {
  return requestClient.post('/infra/file/create-directory', data);
}

/** 搜索文件 */
export async function searchFiles(params: InfraFileApi.FileSearchReqVO) {
  return requestClient.get<PageResult<InfraFileApi.FileRespVO>>(
    '/infra/file/search',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 删除文件 */
export async function deleteFile(id: string) {
  return requestClient.delete(
    `/infra/file/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 批量删除文件 */
export async function deleteFileList(ids: string[]) {
  return requestClient.delete('/infra/file/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}

/** 通过存储 key 删除文件或文件夹 */
export async function deleteByKey(configId: string, key: string) {
  return requestClient.delete('/infra/file/delete-by-key', {
    params: { configId, key },
  });
}

/** 批量通过存储 key 删除文件 */
export async function deleteByKeys(configId: string, keys: string[]) {
  return requestClient.delete('/infra/file/delete-by-keys', {
    params: { configId, keys: keys.join(',') },
  });
}

/** 重命名文件或目录 */
export async function renameFile(data: InfraFileApi.FileRenameReqVO) {
  return requestClient.post('/infra/file/rename', data);
}
