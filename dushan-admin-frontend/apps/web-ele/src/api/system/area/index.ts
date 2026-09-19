import { requestClient } from '#/api/request';

/** 地区端点（`/system/area`，仅 tenant_required 无权限码）。ID 均为雪花字符串。 */
export namespace SystemAreaApi {
  /** 地区节点 RespVO（树形） */
  export interface AreaNodeRespVO {
    children?: AreaNodeRespVO[];
    id: string;
    name: string;
  }
}

/** 获得地区树 */
export async function getAreaTree() {
  return requestClient.get<SystemAreaApi.AreaNodeRespVO[]>('/system/area/tree');
}

/** 获得 IP 对应的地区名 */
export async function getAreaByIp(ip: string) {
  return requestClient.get<string>('/system/area/get-by-ip', {
    params: { ip },
  });
}
