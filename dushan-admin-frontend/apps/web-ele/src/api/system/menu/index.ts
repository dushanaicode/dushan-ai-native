import { requestClient } from '#/api/request';

/** 菜单端点（`/system/permission/menu`）。ID 均为雪花字符串，`parentId` 允许 '0'。 */
export namespace SystemMenuApi {
  /** 菜单类型（后端 kind 字符串枚举，非数字） */
  export type MenuKind = 'action' | 'group' | 'iframe' | 'link' | 'page';

  /** 菜单信息 RespVO */
  export interface MenuRespVO {
    component?: string;
    componentName?: string;
    createTime: string;
    dataPermission?: boolean;
    icon?: string;
    id: string;
    keepAlive?: boolean;
    kind: MenuKind;
    name: string;
    parentId: string;
    path?: string;
    permission?: string;
    sort: number;
    status: number;
    url?: string;
    visible?: boolean;
  }

  /** 菜单创建/修改 ReqVO */
  export interface MenuSaveReqVO {
    alwaysShow?: boolean;
    component?: string;
    componentName?: string;
    dataPermission?: boolean;
    icon?: string;
    id?: string;
    keepAlive?: boolean;
    kind: MenuKind;
    name: string;
    parentId: string;
    path?: string;
    permission?: string;
    sort: number;
    status: number;
    url?: string;
    visible?: boolean;
  }

  /** 菜单列表查询 ReqVO（非分页，返回树所需全量列表） */
  export interface MenuListReqVO {
    name?: string;
    paginate?: boolean;
    status?: number;
  }

  /** 菜单精简信息（分配菜单树用） */
  export interface MenuSimpleRespVO {
    id: string;
    name: string;
    parentId: string;
  }
}

/** 获取菜单列表（树形由前端组装） */
export async function getMenuList(params?: SystemMenuApi.MenuListReqVO) {
  return requestClient.get<SystemMenuApi.MenuRespVO[]>(
    '/system/permission/menu/list',
    { params },
  );
}

/** 获取菜单精简列表 */
export async function getMenuSimpleList() {
  return requestClient.get<SystemMenuApi.MenuSimpleRespVO[]>(
    '/system/permission/menu/simple-list',
  );
}

/** 获取菜单信息 */
export async function getMenu(id: string) {
  return requestClient.get<SystemMenuApi.MenuRespVO>(
    `/system/permission/menu/get?id=${encodeURIComponent(id)}`,
  );
}

/** 创建菜单 */
export async function createMenu(data: SystemMenuApi.MenuSaveReqVO) {
  return requestClient.post('/system/permission/menu/create', data);
}

/** 修改菜单 */
export async function updateMenu(data: SystemMenuApi.MenuSaveReqVO) {
  return requestClient.put('/system/permission/menu/update', data);
}

/** 修改菜单状态 */
export async function updateMenuStatus(id: string, status: number) {
  return requestClient.put('/system/permission/menu/update-status', {
    id,
    status,
  });
}

/** 删除菜单 */
export async function deleteMenu(id: string) {
  return requestClient.delete(
    `/system/permission/menu/delete?id=${encodeURIComponent(id)}`,
  );
}

/** 批量删除菜单 */
export async function deleteMenuList(ids: string[]) {
  return requestClient.delete('/system/permission/menu/delete-list', {
    params: { ids },
    paramsSerializer: 'repeat',
  });
}
