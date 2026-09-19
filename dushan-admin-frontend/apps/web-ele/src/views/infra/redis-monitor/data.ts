import type { InfraRedisMonitorApi } from '#/api/infra/redis-monitor';

export const REDIS_MONITOR_REFRESH_INTERVAL = 10_000;

export interface InfoItem {
  icon: string;
  label: string;
  value: string;
}

export interface MemoryMetricItem {
  label: string;
  value: string;
}

export interface MemoryChartItem {
  name: string;
  value: number;
}

export interface CommandChartItem {
  name: string;
  value: number;
}

export interface CommandRow {
  calls: number;
  command: string;
  usec: number;
}

export interface RedisMonitorData {
  commandStats: InfraRedisMonitorApi.CommandStat[];
  dbSize: number;
  info: InfraRedisMonitorApi.MonitorRespVO['info'];
}

function toFiniteNumber(value: unknown) {
  const numericValue = Number.parseFloat(String(value ?? 0));
  return Number.isFinite(numericValue) ? numericValue : 0;
}

function toInt(value: unknown) {
  return Math.trunc(toFiniteNumber(value));
}

function getInfoValue(
  info: InfraRedisMonitorApi.MonitorRespVO['info'],
  key: string,
  fallback = 'N/A',
) {
  const value = info[key];
  if (value === undefined || value === null || value === '') {
    return fallback;
  }
  return String(value);
}

function formatBooleanFlag(value: unknown) {
  return String(value ?? '0') === '0' ? '否' : '是';
}

function formatMemory(bytes: unknown) {
  const value = toFiniteNumber(bytes);
  if (value <= 0) {
    return '0 B';
  }
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const index = Math.min(
    Math.floor(Math.log(value) / Math.log(1024)),
    units.length - 1,
  );
  return `${(value / 1024 ** index).toFixed(index === 0 ? 0 : 2)} ${units[index]}`;
}

function formatPercent(value: number) {
  return `${value.toFixed(2)}%`;
}

function formatMode(value: unknown) {
  if (value === 'standalone') {
    return '单机';
  }
  if (value === 'cluster') {
    return '集群';
  }
  return String(value || 'N/A');
}

export function normalizeRedisMonitor(
  data?: InfraRedisMonitorApi.MonitorRespVO,
): RedisMonitorData {
  return {
    commandStats: data?.commandStats ?? [],
    dbSize: data?.dbSize ?? 0,
    info: data?.info ?? {},
  };
}

export function useInfoItems(data: RedisMonitorData): InfoItem[] {
  const { dbSize, info } = data;
  const hits = toFiniteNumber(info.keyspace_hits);
  const misses = toFiniteNumber(info.keyspace_misses);
  const hitRate = hits + misses > 0 ? (hits / (hits + misses)) * 100 : 0;

  return [
    {
      icon: 'lucide:badge-info',
      label: 'Redis 版本',
      value: getInfoValue(info, 'redis_version'),
    },
    {
      icon: 'lucide:network',
      label: '运行模式',
      value: formatMode(info.redis_mode),
    },
    {
      icon: 'lucide:plug',
      label: '端口',
      value: getInfoValue(info, 'tcp_port'),
    },
    {
      icon: 'lucide:users',
      label: '客户端数',
      value: getInfoValue(info, 'connected_clients', '0'),
    },
    {
      icon: 'lucide:clock-3',
      label: '运行时间',
      value: `${getInfoValue(info, 'uptime_in_days', '0')} 天`,
    },
    {
      icon: 'lucide:database',
      label: 'Key 数量',
      value: String(dbSize),
    },
    {
      icon: 'lucide:activity',
      label: '每秒命令数',
      value: getInfoValue(info, 'instantaneous_ops_per_sec', '0'),
    },
    {
      icon: 'lucide:timer',
      label: '命中率',
      value: formatPercent(hitRate),
    },
    {
      icon: 'lucide:hard-drive',
      label: '使用内存',
      value: formatMemory(info.used_memory),
    },
    {
      icon: 'lucide:shield-check',
      label: 'AOF 开启',
      value: formatBooleanFlag(info.aof_enabled),
    },
    {
      icon: 'lucide:save',
      label: 'RDB 状态',
      value: getInfoValue(info, 'rdb_last_bgsave_status'),
    },
    {
      icon: 'lucide:arrow-left-right',
      label: '网络入口/出口',
      value: `${getInfoValue(info, 'instantaneous_input_kbps', '0')} KB/s / ${getInfoValue(info, 'instantaneous_output_kbps', '0')} KB/s`,
    },
  ];
}

export function useMemoryMetrics(data: RedisMonitorData): MemoryMetricItem[] {
  const { info } = data;
  return [
    { label: '当前内存', value: formatMemory(info.used_memory) },
    { label: '峰值内存', value: formatMemory(info.used_memory_peak) },
    { label: 'RSS 内存', value: formatMemory(info.used_memory_rss) },
    {
      label: '碎片率',
      value: getInfoValue(info, 'mem_fragmentation_ratio', '0'),
    },
    {
      label: '最大内存',
      value:
        getInfoValue(info, 'maxmemory_human', '') ||
        formatMemory(info.maxmemory),
    },
    {
      label: '淘汰策略',
      value: getInfoValue(info, 'maxmemory_policy'),
    },
  ];
}

export function useMemoryChartData(data: RedisMonitorData): MemoryChartItem[] {
  const { info } = data;
  return [
    { name: '当前内存', value: toFiniteNumber(info.used_memory) / 1024 / 1024 },
    {
      name: '峰值内存',
      value: toFiniteNumber(info.used_memory_peak) / 1024 / 1024,
    },
    {
      name: 'RSS 内存',
      value: toFiniteNumber(info.used_memory_rss) / 1024 / 1024,
    },
  ];
}

export function useCommandRows(data: RedisMonitorData): CommandRow[] {
  return [...data.commandStats]
    .map((item) => ({
      calls: toInt(item.calls),
      command: item.command,
      usec: toInt(item.usec),
    }))
    .toSorted((left, right) => right.calls - left.calls);
}

export function useCommandChartData(
  data: RedisMonitorData,
): CommandChartItem[] {
  return useCommandRows(data)
    .slice(0, 12)
    .map((item) => ({
      name: item.command,
      value: item.calls,
    }));
}
