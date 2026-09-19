import { requestClient } from '#/api/request';

/** 服务器监控端点（`/infra/server`）。 */
export namespace InfraServerApi {
  /** CPU 信息 */
  export interface CpuInfoVO {
    cpuNum?: number;
    free?: number;
    sys?: number;
    used?: number;
  }

  /** 内存信息 */
  export interface MemoryInfoVO {
    free?: string;
    total?: string;
    usage?: number;
    used?: string;
  }

  /** Python 进程信息 */
  export interface PyInfoVO extends MemoryInfoVO {
    home?: string;
    name?: string;
    runTime?: string;
    startTime?: string;
    version?: string;
  }

  /** 系统信息 */
  export interface SysInfoVO {
    computerIp?: string;
    computerName?: string;
    osArch?: string;
    osName?: string;
    userDir?: string;
  }

  /** 磁盘信息 */
  export interface SysFilesVO {
    dirName?: string;
    free?: string;
    sysTypeName?: string;
    total?: string;
    typeName?: string;
    usage?: string;
    used?: string;
  }

  /** 服务监控信息 RespVO */
  export interface ServerMonitorRespVO {
    cpu: CpuInfoVO;
    mem: MemoryInfoVO;
    py: PyInfoVO;
    sys: SysInfoVO;
    sysFiles: SysFilesVO[];
  }
}

/** 获取服务器信息 */
export async function getServerInfo() {
  return requestClient.get<InfraServerApi.ServerMonitorRespVO>(
    '/infra/server/list',
  );
}
