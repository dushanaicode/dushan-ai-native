import type { ExportField, PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 用户端点（`/system/user`）。ID 均为雪花字符串。 */
export namespace SystemUserApi {
  /** 用户信息 RespVO */
  export interface UserRespVO {
    avatar?: string;
    createTime: string;
    deptId?: string;
    deptName?: string;
    email?: string;
    id: string;
    loginDate?: string;
    loginIp?: string;
    mobile?: string;
    nickname: string;
    postIds?: string[];
    remark?: string;
    sex?: number;
    status: number;
    username: string;
  }

  /** 用户创建/修改 ReqVO；password 创建必填（4-16 位），更新不传 */
  export interface UserSaveReqVO {
    avatar?: string;
    deptId?: string;
    email?: string;
    id?: string;
    mobile?: string;
    nickname: string;
    password?: string;
    postIds?: string[];
    remark?: string;
    sex?: number;
    username: string;
  }

  /** 用户分页查询 ReqVO */
  export interface UserPageReqVO extends PageParam {
    createTime?: string[];
    deptId?: string;
    fields?: string[];
    mobile?: string;
    roleId?: string;
    status?: number;
    username?: string;
  }

  /** 用户精简信息 */
  export interface UserSimpleRespVO {
    deptId?: string;
    deptName?: string;
    id: string;
    nickname: string;
  }

  /** 用户导入 RespVO */
  export interface UserImportRespVO {
    createUsernames: string[];
    failureUsernames: Record<string, string>;
    updateUsernames: string[];
  }
}

/** 查询用户分页 */
export async function getUserPage(params: SystemUserApi.UserPageReqVO) {
  return requestClient.get<PageResult<SystemUserApi.UserRespVO>>(
    '/system/user/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 获取用户精简列表（开启状态，下拉选项用） */
export async function getSimpleUserList() {
  return requestClient.get<SystemUserApi.UserSimpleRespVO[]>(
    '/system/user/simple-list',
  );
}

/** 查询用户详情 */
export async function getUser(id: string) {
  return requestClient.get<SystemUserApi.UserRespVO>(
    `/system/user/get?id=${encodeURIComponent(id)}`,
  );
}

/** 新增用户 */
export async function createUser(data: SystemUserApi.UserSaveReqVO) {
  return requestClient.post('/system/user/create', data);
}

/** 修改用户 */
export async function updateUser(data: SystemUserApi.UserSaveReqVO) {
  return requestClient.put('/system/user/update', data);
}

/** 删除用户 */
export async function deleteUser(id: string) {
  return requestClient.delete(
    `/system/user/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 批量删除用户 */
export async function deleteUserList(ids: string[]) {
  return requestClient.delete('/system/user/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}

/** 重置用户密码 */
export async function updateUserPassword(id: string, password: string) {
  return requestClient.put('/system/user/update-password', { id, password });
}

/** 修改用户状态 */
export async function updateUserStatus(id: string, status: number) {
  return requestClient.put('/system/user/update-status', { id, status });
}

/** 获取用户可导出字段列表 */
export async function getExportUserFields() {
  return requestClient.get<ExportField[]>('/system/user/export-fields');
}

/** 导出用户 Excel */
export async function exportUser(params: SystemUserApi.UserPageReqVO) {
  return requestClient.download('/system/user/export-excel', {
    params,
    paramsSerializer: 'repeat',
  });
}

/** 获得导入用户模板 */
export async function importUserTemplate() {
  return requestClient.download('/system/user/get-import-template');
}

/** 导入用户（multipart：file + updateSupport） */
export async function importUser(file: File, updateSupport: boolean) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('updateSupport', String(updateSupport));
  return requestClient.post<SystemUserApi.UserImportRespVO>(
    '/system/user/import',
    formData,
  );
}
