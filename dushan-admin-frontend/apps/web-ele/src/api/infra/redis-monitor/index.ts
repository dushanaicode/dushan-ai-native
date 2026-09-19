import { requestClient } from '#/api/request';

/** 缓存监控端点（`/infra/cache`）。 */
export namespace InfraRedisMonitorApi {
  /** Redis 命令统计 */
  export interface CommandStat {
    calls: number;
    command: string;
    usec: number;
  }

  /** 缓存监控信息 RespVO */
  export interface MonitorRespVO {
    commandStats: CommandStat[];
    dbSize: number;
    info: Record<string, unknown>;
  }
}

/** 获得缓存监控信息 */
export async function getCacheMonitorInfo() {
  return requestClient.get<InfraRedisMonitorApi.MonitorRespVO>(
    '/infra/cache/get-monitor-info',
  );
}
