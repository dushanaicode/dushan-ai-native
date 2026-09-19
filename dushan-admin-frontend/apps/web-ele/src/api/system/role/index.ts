import type { ExportField, PageParam, PageResult } from '#/api/types';

import { requestClient } from '#/api/request';

/** 角色端点（`/system/permission/role`）与权限分配端点（`/system/permission`）。ID 均为雪花字符串。 */
export namespace SystemRoleApi {
  /** 角色信息 RespVO */
  export interface RoleRespVO {
    builtin: number;
    code: string;
    createTime: string;
    dataScope: number;
    dataScopeDeptIds?: string[];
    id: string;
    name: string;
    remark?: string;
    sort: number;
    status: number;
  }

  /** 角色创建/更新 ReqVO（不含 status，状态走 update-status） */
  export interface RoleSaveReqVO {
    code: string;
    id?: string;
    name: string;
    remark?: string;
    sort: number;
  }

  /** 角色分页查询 ReqVO */
  export interface RolePageReqVO extends PageParam {
    code?: string;
    createTime?: string[];
    name?: string;
    status?: number;
  }

  /** 角色精简信息 */
  export interface RoleSimpleRespVO {
    id: string;
    name: string;
  }
}

/** 查询角色分页 */
export async function getRolePage(params: SystemRoleApi.RolePageReqVO) {
  return requestClient.get<PageResult<SystemRoleApi.RoleRespVO>>(
    '/system/permission/role/page',
    { params, paramsSerializer: 'repeat' },
  );
}

/** 获取角色精简列表 */
export async function getSimpleRoleList() {
  return requestClient.get<SystemRoleApi.RoleSimpleRespVO[]>(
    '/system/permission/role/simple-list',
  );
}

/** 查询角色详情 */
export async function getRole(id: string) {
  return requestClient.get<SystemRoleApi.RoleRespVO>(
    `/system/permission/role/get?id=${encodeURIComponent(id)}`,
  );
}

/** 新增角色 */
export async function createRole(data: SystemRoleApi.RoleSaveReqVO) {
  return requestClient.post('/system/permission/role/create', data);
}

/** 修改角色 */
export async function updateRole(data: SystemRoleApi.RoleSaveReqVO) {
  return requestClient.put('/system/permission/role/update', data);
}

/** 修改角色状态 */
export async function updateRoleStatus(id: string, status: number) {
  return requestClient.put('/system/permission/role/update-status', {
    id,
    status,
  });
}

/** 删除角色 */
export async function deleteRole(id: string) {
  return requestClient.delete(
    `/system/permission/role/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 批量删除角色 */
export async function deleteRoleList(ids: string[]) {
  return requestClient.delete('/system/permission/role/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}

/** 获取角色可导出字段列表 */
export async function getExportRoleFields() {
  return requestClient.get<ExportField[]>(
    '/system/permission/role/export-fields',
  );
}

/** 导出角色 Excel */
export async function exportRole(params: SystemRoleApi.RolePageReqVO) {
  return requestClient.download('/system/permission/role/export-excel', {
    params,
    paramsSerializer: 'repeat',
  });
}

/** 获得角色拥有的菜单编号（后端返回数字集合，统一转为字符串） */
export async function getRoleMenuList(roleId: string) {
  const ids = await requestClient.get<(number | string)[]>(
    '/system/permission/list-role-menus',
    { params: { roleId } },
  );
  return ids.map(String);
}

/** 获得多个角色拥有的菜单编号 */
export async function getRoleMenuListByIds(roleIds: string[]) {
  const ids = await requestClient.get<(number | string)[]>(
    '/system/permission/list-role-menus-by-ids',
    { params: { roleIds }, paramsSerializer: 'repeat' },
  );
  return ids.map(String);
}

/** 赋予角色菜单 */
export async function assignRoleMenu(roleId: string, menuIds: string[]) {
  return requestClient.post('/system/permission/assign-role-menu', {
    menuIds,
    roleId,
  });
}

/** 赋予角色数据权限 */
export async function assignRoleDataScope(
  roleId: string,
  dataScope: number,
  dataScopeDeptIds?: string[],
) {
  return requestClient.post('/system/permission/assign-role-data-scope', {
    dataScope,
    dataScopeDeptIds,
    roleId,
  });
}

/** 获得管理员拥有的角色编号列表 */
export async function getUserRoleList(userId: string) {
  const ids = await requestClient.get<(number | string)[]>(
    '/system/permission/list-user-roles',
    { params: { userId } },
  );
  return ids.map(String);
}

/** 赋予用户角色 */
export async function assignUserRole(userId: string, roleIds: string[]) {
  return requestClient.post('/system/permission/assign-user-role', {
    roleIds,
    userId,
  });
}
