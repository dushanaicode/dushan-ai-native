import { requestClient } from '#/api/request';

/** 部门端点（`/system/dept`）。ID 均为雪花字符串，`parentId` 允许 '0'。 */
export namespace SystemDeptApi {
  /** 部门信息 RespVO */
  export interface DeptRespVO {
    createTime: string;
    email?: string;
    id: string;
    leaderUserId?: string;
    name: string;
    parentId?: string;
    phone?: string;
    sort: number;
    status: number;
  }

  /** 部门创建/修改 ReqVO */
  export interface DeptSaveReqVO {
    email?: string;
    id?: string;
    leaderUserId?: string;
    name: string;
    parentId?: string;
    phone?: string;
    sort: number;
    status: number;
  }

  /** 部门列表查询 ReqVO（非分页） */
  export interface DeptListReqVO {
    name?: string;
    status?: number;
  }

  /** 部门精简信息 */
  export interface DeptSimpleRespVO {
    id: string;
    name: string;
    parentId: string;
  }
}

/** 获取部门列表（树形由前端组装） */
export async function getDeptList(params?: SystemDeptApi.DeptListReqVO) {
  return requestClient.get<SystemDeptApi.DeptRespVO[]>('/system/dept/list', {
    params,
  });
}

/** 获取部门精简列表 */
export async function getSimpleDeptList() {
  return requestClient.get<SystemDeptApi.DeptSimpleRespVO[]>(
    '/system/dept/simple-list',
  );
}

/** 查询部门详情 */
export async function getDept(id: string) {
  return requestClient.get<SystemDeptApi.DeptRespVO>(
    `/system/dept/get?id=${encodeURIComponent(id)}`,
  );
}

/** 新增部门 */
export async function createDept(data: SystemDeptApi.DeptSaveReqVO) {
  return requestClient.post('/system/dept/create', data);
}

/** 修改部门 */
export async function updateDept(data: SystemDeptApi.DeptSaveReqVO) {
  return requestClient.put('/system/dept/update', data);
}

/** 修改部门状态 */
export async function updateDeptStatus(id: string, status: number) {
  return requestClient.put('/system/dept/update-status', { id, status });
}

/** 删除部门 */
export async function deleteDept(id: string) {
  return requestClient.delete(
    `/system/dept/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 批量删除部门 */
export async function deleteDeptList(ids: string[]) {
  return requestClient.delete('/system/dept/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}
