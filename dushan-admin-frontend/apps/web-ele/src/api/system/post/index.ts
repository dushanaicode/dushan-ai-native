import type { ExportField, PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 岗位端点（后端挂在 `/system/dept/post` 前缀下）。ID 均为雪花字符串。 */
export namespace SystemPostApi {
  /** 岗位信息 RespVO */
  export interface PostRespVO {
    code: string;
    createTime: string;
    id: string;
    name: string;
    remark?: string;
    sort: number;
    status: number;
  }

  /** 岗位创建/修改 ReqVO */
  export interface PostSaveReqVO {
    code: string;
    id?: string;
    name: string;
    remark?: string;
    sort: number;
    status: number;
  }

  /** 岗位分页查询 ReqVO */
  export interface PostPageReqVO extends PageParam {
    code?: string;
    createTime?: string[];
    name?: string;
    status?: number;
  }

  /** 岗位精简信息 */
  export interface PostSimpleRespVO {
    id: string;
    name: string;
  }
}

/** 获取岗位精简列表 */
export async function getSimplePostList() {
  return requestClient.get<SystemPostApi.PostSimpleRespVO[]>(
    '/system/dept/post/simple-list',
  );
}

/** 查询岗位分页 */
export async function getPostPage(params: SystemPostApi.PostPageReqVO) {
  return requestClient.get<PageResult<SystemPostApi.PostRespVO>>(
    '/system/dept/post/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 查询岗位详情 */
export async function getPost(id: string) {
  return requestClient.get<SystemPostApi.PostRespVO>(
    `/system/dept/post/get?id=${encodeURIComponent(id)}`,
  );
}

/** 新增岗位 */
export async function createPost(data: SystemPostApi.PostSaveReqVO) {
  return requestClient.post('/system/dept/post/create', data);
}

/** 修改岗位 */
export async function updatePost(data: SystemPostApi.PostSaveReqVO) {
  return requestClient.put('/system/dept/post/update', data);
}

/** 修改岗位状态 */
export async function updatePostStatus(id: string, status: number) {
  return requestClient.put('/system/dept/post/update-status', { id, status });
}

/** 删除岗位 */
export async function deletePost(id: string) {
  return requestClient.delete(
    `/system/dept/post/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 批量删除岗位 */
export async function deletePostList(ids: string[]) {
  return requestClient.delete('/system/dept/post/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}

/** 获取岗位可导出字段列表 */
export async function getExportPostFields() {
  return requestClient.get<ExportField[]>('/system/dept/post/export-fields');
}

/** 导出岗位 Excel */
export async function exportPost(params: SystemPostApi.PostPageReqVO) {
  return requestClient.download('/system/dept/post/export-excel', {
    params,
    paramsSerializer: 'repeat',
  });
}
