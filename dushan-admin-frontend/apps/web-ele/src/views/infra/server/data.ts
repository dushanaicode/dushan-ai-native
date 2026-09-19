import type { InfraServerApi } from '#/api/infra/server';

export const SERVER_MONITOR_REFRESH_INTERVAL = 10_000;

export interface MetricItem {
  danger?: boolean;
  label: string;
  suffix?: string;
  value?: null | number | string;
}

export interface SecondaryMetric {
  label: string;
  usage: number;
}

export interface MetricCardData {
  icon: string;
  items: MetricItem[];
  secondary?: SecondaryMetric;
  title: string;
  usage: number;
  usageLabel: string;
}

export interface InfoItem {
  label: string;
  span?: number;
  value?: null | string;
}

export interface InfoCardData {
  icon: string;
  items: InfoItem[];
  title: string;
}

export interface DiskRow {
  danger: boolean;
  dirName?: null | string;
  free?: null | string;
  sysTypeName?: null | string;
  total?: null | string;
  typeName?: null | string;
  usage?: null | string;
  usagePercent: number;
  used?: null | string;
}

function toFiniteNumber(value: null | number | string | undefined) {
  const numericValue = Number.parseFloat(String(value ?? 0).replace('%', ''));
  return Number.isFinite(numericValue) ? numericValue : 0;
}

export function normalizePercent(value: null | number | string | undefined) {
  return Math.min(Math.max(toFiniteNumber(value), 0), 100);
}

export function getPercentStatus(usage: number) {
  if (usage >= 90) {
    return 'exception';
  }
  if (usage >= 75) {
    return 'warning';
  }
  return 'success';
}

export function formatCellValue(value: null | number | string | undefined) {
  if (value === undefined || value === null || value === '') {
    return 'N/A';
  }
  return value;
}

export function useCpuCard(
  server: InfraServerApi.ServerMonitorRespVO | undefined,
): MetricCardData {
  const userUsage = normalizePercent(server?.cpu?.used);
  const systemUsage = normalizePercent(server?.cpu?.sys);
  const usage = normalizePercent(userUsage + systemUsage);

  return {
    icon: 'lucide:cpu',
    items: [
      { label: '核心数', value: server?.cpu?.cpuNum },
      { label: '用户使用率', suffix: '%', value: server?.cpu?.used },
      { label: '系统使用率', suffix: '%', value: server?.cpu?.sys },
      { label: '当前空闲率', suffix: '%', value: server?.cpu?.free },
    ],
    title: 'CPU',
    usage,
    usageLabel: '总使用率',
  };
}

export function useMemoryCard(
  server: InfraServerApi.ServerMonitorRespVO | undefined,
): MetricCardData {
  const memoryUsage = normalizePercent(server?.mem?.usage);
  const pythonUsage = normalizePercent(server?.py?.usage);

  return {
    icon: 'lucide:memory-stick',
    items: [
      { label: '内存总量', value: server?.mem?.total },
      { label: '内存已用', value: server?.mem?.used },
      { label: '内存剩余', value: server?.mem?.free },
      {
        danger: memoryUsage >= 75,
        label: '内存使用率',
        suffix: '%',
        value: server?.mem?.usage,
      },
      { label: 'Python 已用', value: server?.py?.used },
      {
        danger: pythonUsage >= 75,
        label: 'Python 使用率',
        suffix: '%',
        value: server?.py?.usage,
      },
    ],
    secondary: {
      label: 'Python',
      usage: pythonUsage,
    },
    title: '内存',
    usage: memoryUsage,
    usageLabel: '系统内存',
  };
}

export function useServerInfoCard(
  server: InfraServerApi.ServerMonitorRespVO | undefined,
): InfoCardData {
  return {
    icon: 'lucide:server',
    items: [
      { label: '服务器名称', value: server?.sys?.computerName },
      { label: '操作系统', value: server?.sys?.osName },
      { label: '服务器 IP', value: server?.sys?.computerIp },
      { label: '系统架构', value: server?.sys?.osArch },
      { label: '项目路径', span: 2, value: server?.sys?.userDir },
    ],
    title: '服务器信息',
  };
}

export function usePythonInfoCard(
  server: InfraServerApi.ServerMonitorRespVO | undefined,
): InfoCardData {
  return {
    icon: 'lucide:terminal',
    items: [
      { label: 'Python 名称', value: server?.py?.name },
      { label: 'Python 版本', value: server?.py?.version },
      { label: '启动时间', value: server?.py?.startTime },
      { label: '运行时长', value: server?.py?.runTime },
      { label: '安装路径', span: 2, value: server?.py?.home },
    ],
    title: 'Python 进程信息',
  };
}

export function useDiskRows(
  server: InfraServerApi.ServerMonitorRespVO | undefined,
): DiskRow[] {
  return (server?.sysFiles ?? []).map((item) => {
    const usagePercent = normalizePercent(item.usage);
    return {
      danger: usagePercent >= 75,
      dirName: item.dirName,
      free: item.free,
      sysTypeName: item.sysTypeName,
      total: item.total,
      typeName: item.typeName,
      usage: item.usage,
      usagePercent,
      used: item.used,
    };
  });
}
