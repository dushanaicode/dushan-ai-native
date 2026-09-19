import type { InfraRedisCacheApi } from '#/api/infra/redis-cache';

export const CACHE_QUERY_PERMISSION = 'infra:cache:get-names';
export const CACHE_DELETE_PERMISSION = 'infra:cache:get-names';
export const DEFAULT_SCAN_PATTERN = '*';
export const REDIS_CACHE_PAGE_SIZE = 1000;

export type RedisKeyTagType =
  | 'danger'
  | 'info'
  | 'primary'
  | 'success'
  | 'warning';

export interface RedisCacheTreeNode {
  children?: RedisCacheTreeNode[];
  count: number;
  dbName: string;
  fullKey?: string;
  id: string;
  isLeaf: boolean;
  label: string;
}

export interface RedisCacheKeyRow {
  key: string;
}

export interface RedisValueView {
  isJson: boolean;
  jsonValue: unknown;
  textValue: string;
}

interface TrieNode {
  children: Map<string, TrieNode>;
  fullKey?: string;
  isKey: boolean;
}

function createTrieNode(): TrieNode {
  return {
    children: new Map<string, TrieNode>(),
    isKey: false,
  };
}

function countLeaves(node: TrieNode): number {
  let count = node.isKey ? 1 : 0;
  for (const child of node.children.values()) {
    count += countLeaves(child);
  }
  return count;
}

function toTreeNodes(
  entries: IterableIterator<[string, TrieNode]>,
  dbName: string,
  prefix = '',
): RedisCacheTreeNode[] {
  return [...entries]
    .map(([label, node]) => {
      const id = prefix ? `${prefix}:${label}` : label;
      const children = toTreeNodes(node.children.entries(), dbName, id);
      const isLeaf = node.isKey && children.length === 0;

      return {
        children: isLeaf ? undefined : children,
        count: countLeaves(node),
        dbName,
        fullKey: node.fullKey,
        id,
        isLeaf,
        label,
      };
    })
    .toSorted((left, right) => {
      if (left.isLeaf !== right.isLeaf) {
        return left.isLeaf ? 1 : -1;
      }
      return left.label.localeCompare(right.label);
    });
}

/** 构建 Redis key 树 */
export function buildRedisKeyTree(
  keys: string[],
  dbName: string,
): RedisCacheTreeNode[] {
  const root = createTrieNode();

  for (const key of keys) {
    const parts = key.split(':').filter(Boolean);
    let current = root;

    for (const [index, part] of parts.entries()) {
      const next = current.children.get(part) ?? createTrieNode();
      current.children.set(part, next);

      if (index === parts.length - 1) {
        next.isKey = true;
        next.fullKey = key;
      }

      current = next;
    }
  }

  return toTreeNodes(root.children.entries(), dbName);
}

/** 格式化 TTL */
export function formatTtl(ttl?: number) {
  if (ttl === undefined) {
    return '-';
  }
  if (ttl === -1) {
    return '永不过期';
  }
  if (ttl === -2) {
    return '已过期';
  }
  if (ttl >= 86_400) {
    return `${Math.floor(ttl / 86_400)}d ${Math.floor((ttl % 86_400) / 3600)}h`;
  }
  if (ttl >= 3600) {
    return `${Math.floor(ttl / 3600)}h ${Math.floor((ttl % 3600) / 60)}m`;
  }
  if (ttl >= 60) {
    return `${Math.floor(ttl / 60)}m ${ttl % 60}s`;
  }
  return `${ttl}s`;
}

/** Redis 类型标签 */
export function getKeyTypeTagType(keyType?: string): RedisKeyTagType {
  const typeMap: Record<string, RedisKeyTagType> = {
    hash: 'success',
    list: 'warning',
    set: 'danger',
    string: 'primary',
    zset: 'info',
  };

  return typeMap[keyType ?? ''] ?? 'info';
}

function stringifyValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '';
  }
  if (typeof value === 'string') {
    return value;
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

/** 归一化缓存值展示 */
export function normalizeRedisValue(value: unknown): RedisValueView {
  const textValue = stringifyValue(value);
  const trimmed = textValue.trim();

  if (
    (trimmed.startsWith('{') && trimmed.endsWith('}')) ||
    (trimmed.startsWith('[') && trimmed.endsWith(']'))
  ) {
    try {
      return {
        isJson: true,
        jsonValue: JSON.parse(trimmed),
        textValue,
      };
    } catch {
      // 按普通文本展示。
    }
  }

  return {
    isJson: false,
    jsonValue: undefined,
    textValue,
  };
}

/** 缓存 key 表格行 */
export function toCacheKeyRows(keys: string[]): RedisCacheKeyRow[] {
  return keys.map((key) => ({ key }));
}

/** 缓存分组说明 */
export function getCacheGroupRemark(
  group?: InfraRedisCacheApi.CacheInfoRespVO | null,
) {
  const value = group?.cacheValue;
  if (value === null || value === undefined || value === '') {
    return '-';
  }
  return String(value);
}
