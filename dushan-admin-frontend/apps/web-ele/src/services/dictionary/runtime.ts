import type { Ref } from 'vue';

import type { SessionCoordinator } from '../session/coordinator';
import type {
  DictionaryEntry,
  DictionaryValue,
  DictionaryValueType,
} from './types';

import { shallowRef, watch } from 'vue';

import { z } from '@vben/common-ui';

const entrySchema = z
  .object({
    dictType: z.string().min(1),
    label: z.string().min(1),
    value: z.string().min(1),
    colorType: z.string().min(1).nullable().optional(),
    permission: z.string().nullable().optional(),
    tagStyle: z
      .object({
        color: z.string(),
        textColor: z.string(),
        variant: z.enum(['solid', 'outline', 'text', 'link']),
      })
      .strict()
      .nullable()
      .optional(),
  })
  .strict();

type DictionaryIndex = Map<string, Map<string, Readonly<DictionaryEntry>>>;

export class DictionaryRuntime {
  get error() {
    return this.state.value.error;
  }
  get status() {
    return this.state.value.status;
  }
  get version() {
    return this.state.value.version;
  }
  private disposed = false;
  private pending:
    | undefined
    | { controller: AbortController; promise: Promise<void> };
  private revision = 0;
  private state = shallowRef<{
    data: DictionaryIndex;
    error: unknown;
    status: 'error' | 'idle' | 'loading' | 'ready';
    version: number;
  }>({ data: new Map(), error: undefined, status: 'idle', version: 0 });

  private stopLocale: () => void;

  private stopSession: () => void;
  constructor(
    private readonly options: {
      loader: (signal: AbortSignal, locale: string) => Promise<unknown>;
      locale: Readonly<Ref<string>>;
      session: SessionCoordinator;
    },
  ) {
    this.stopSession = options.session.subscribe((next, previous) => {
      if (next.generation !== previous.generation) this.invalidate();
    });
    this.stopLocale = watch(options.locale, () => this.invalidate(), {
      flush: 'sync',
    });
    options.session.signal.addEventListener('abort', this.onSessionDisposed, {
      once: true,
    });
  }
  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    this.pending?.controller.abort();
    this.stopLocale();
    this.stopSession();
    this.options.session.signal.removeEventListener(
      'abort',
      this.onSessionDisposed,
    );
    this.state.value = {
      data: new Map(),
      error: undefined,
      status: 'idle',
      version: this.version,
    };
  }

  ensure(): Promise<void> {
    if (this.disposed)
      return Promise.reject(
        new DOMException('字典实例已关闭', 'InvalidStateError'),
      );
    const scope = this.options.session.capture();
    if (this.status === 'ready') return Promise.resolve();
    if (this.pending) return this.pending.promise;
    const revision = this.revision;
    const locale = this.options.locale.value;
    const controller = new AbortController();
    this.state.value = {
      ...this.state.value,
      error: undefined,
      status: 'loading',
    };
    const promise = Promise.resolve()
      .then(() => {
        controller.signal.throwIfAborted();
        return this.options.loader(controller.signal, locale);
      })
      .then((value) => {
        this.options.session.assertCurrent(scope);
        if (revision !== this.revision)
          throw new DOMException('字典加载已失效', 'AbortError');
        controller.signal.throwIfAborted();
        const entries = z.array(entrySchema).parse(value);
        const data: DictionaryIndex = new Map();
        for (const entry of entries) {
          let group = data.get(entry.dictType);
          if (!group) {
            group = new Map();
            data.set(entry.dictType, group);
          }
          if (group.has(entry.value))
            throw new TypeError(`字典值重复：${entry.dictType}/${entry.value}`);
          if (entry.tagStyle) Object.freeze(entry.tagStyle);
          group.set(entry.value, Object.freeze(entry));
        }
        this.state.value = {
          data,
          status: 'ready',
          error: undefined,
          version: this.version + 1,
        };
      })
      .catch((error: unknown) => {
        if (this.disposed || revision !== this.revision)
          throw new DOMException('字典加载已失效', 'AbortError');
        this.options.session.assertCurrent(scope);
        this.state.value = { ...this.state.value, error, status: 'error' };
        throw error;
      })
      .finally(() => {
        if (this.pending?.promise === promise) this.pending = undefined;
      });
    this.pending = { controller, promise };
    return promise;
  }

  getDictData(type: string, value: DictionaryValue) {
    return this.state.value.data.get(type)?.get(String(value));
  }

  getDictLabel(type: string, value: DictionaryValue) {
    return this.getDictData(type, value)?.label ?? String(value);
  }

  getDictOptions(type: string, valueType: DictionaryValueType) {
    const entries = this.state.value.data.get(type);
    return entries
      ? [...entries.values()].map((entry) => ({
          ...entry,
          value: convertDictionaryValue(entry.value, valueType),
        }))
      : [];
  }

  invalidate() {
    this.revision += 1;
    this.pending?.controller.abort();
    this.pending = undefined;
    this.state.value = {
      data: new Map(),
      error: undefined,
      status: 'idle',
      version: this.version + 1,
    };
  }

  load() {
    this.invalidate();
    return this.ensure();
  }

  private onSessionDisposed = () => this.dispose();
}

export function convertDictionaryValue(
  value: string,
  type: DictionaryValueType,
): DictionaryValue {
  if (type === 'string') return value;
  if (type === 'boolean') {
    if (value === 'true') return true;
    if (value === 'false') return false;
    throw new TypeError(`布尔字典值必须是 true 或 false：${value}`);
  }
  if (!/^-?\d+$/.test(value) || !Number.isSafeInteger(Number(value)))
    throw new TypeError(`数字字典值必须是安全整数：${value}`);
  return Number(value);
}
