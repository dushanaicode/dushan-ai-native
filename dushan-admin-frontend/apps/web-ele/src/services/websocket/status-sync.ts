import type { SessionCoordinator } from '../session/coordinator';

import { onScopeDispose } from 'vue';

import { z } from '@vben/common-ui';

const statusSchema = z
  .object({
    taskType: z.string().min(1),
    id: z.string().min(1),
    generation: z.number().int().nonnegative(),
    status: z.enum(['progress', 'success', 'failure']),
    statusCode: z.union([z.string(), z.number(), z.boolean()]).optional(),
    parentId: z.string().nullable().optional(),
    extra: z.record(z.string(), z.unknown()).optional(),
  })
  .strict();
export type StatusChange = z.infer<typeof statusSchema>;
type StatusHandler = (change: StatusChange) => Promise<void> | void;

export class StatusRegistry {
  private disposed = false;
  private groups = new Map<string, Set<StatusHandler>>();
  private stop: () => void;

  constructor(readonly session: SessionCoordinator) {
    this.stop = session.subscribe((next, previous) => {
      if (next.generation !== previous.generation) this.groups.clear();
    });
    session.signal.addEventListener('abort', this.onDispose, { once: true });
  }

  async dispatch(value: unknown) {
    if (this.disposed)
      throw new DOMException('状态订阅已关闭', 'InvalidStateError');
    const change = statusSchema.parse(value);
    const scope = this.session.capture();
    const handlers = [...(this.groups.get(change.taskType) ?? [])];
    const results = await Promise.allSettled(
      handlers.map((handler) =>
        Promise.resolve().then(() => {
          if (
            !this.disposed &&
            this.session.capture().generation === scope.generation &&
            this.groups.get(change.taskType)?.has(handler)
          )
            return handler(change);
        }),
      ),
    );
    if (this.disposed || this.session.capture().generation !== scope.generation)
      return;
    const errors = results
      .filter((result) => result.status === 'rejected')
      .map((result) => result.reason);
    if (errors.length > 0) throw new AggregateError(errors, '状态订阅处理失败');
  }

  dispose() {
    this.disposed = true;
    this.stop();
    this.groups.clear();
    this.session.signal.removeEventListener('abort', this.onDispose);
  }

  onStatusChange(taskType: string, handler: StatusHandler) {
    if (this.disposed)
      throw new DOMException('状态订阅已关闭', 'InvalidStateError');
    let group = this.groups.get(taskType);
    if (!group) {
      group = new Set();
      this.groups.set(taskType, group);
    }
    const handlers = group;
    handlers.add(handler);
    return () => {
      handlers.delete(handler);
      if (handlers.size === 0 && this.groups.get(taskType) === handlers)
        this.groups.delete(taskType);
    };
  }
  private onDispose = () => this.dispose();
}

export function bindStatusRows<Row>(options: {
  registry: StatusRegistry;
  taskType: string;
  getRows: () => Row[];
  getId: (row: Row) => string;
  getVersion: (row: Row) => { generation: number; terminal: boolean };
  apply: (row: Row, change: StatusChange) => void;
  accepts?: (change: StatusChange) => boolean;
  onChange?: (change: StatusChange) => void;
}) {
  const versions = new Map<string, { generation: number; terminal: boolean }>();
  const release = options.registry.onStatusChange(
    options.taskType,
    (change) => {
      if (options.accepts && !options.accepts(change)) return;
      const rows = options.getRows();
      const ids = new Set(rows.map((row) => options.getId(row)));
      for (const id of versions.keys()) if (!ids.has(id)) versions.delete(id);
      const row = rows.find((item) => options.getId(item) === change.id);
      if (!row) {
        options.onChange?.(change);
        return;
      }
      const actual = options.getVersion(row);
      const remembered = versions.get(change.id);
      const current =
        remembered && remembered.generation >= actual.generation
          ? remembered
          : actual;
      if (
        change.generation < current.generation ||
        (current.terminal && change.generation <= current.generation)
      )
        return;
      options.apply(row, change);
      versions.set(change.id, {
        generation: change.generation,
        terminal: change.status !== 'progress',
      });
      options.onChange?.(change);
    },
  );
  return () => {
    release();
    versions.clear();
  };
}

export function useWsStatusSync<Row>(
  options: Parameters<typeof bindStatusRows<Row>>[0],
) {
  const release = bindStatusRows(options);
  onScopeDispose(release);
  return release;
}
