import { shallowRef } from 'vue';

import { z } from '@vben/common-ui';

const fileSchema = z
  .object({
    id: z.string().min(1),
    name: z.string().min(1),
    size: z.number().int().nonnegative(),
    mediaType: z.string().min(1),
  })
  .strict();
const accessSchema = fileSchema.extend({ url: z.string().min(1) });
export type StoredFile = z.infer<typeof fileSchema>;
export type FileAccess = z.infer<typeof accessSchema>;
export type FileValue = string | string[] | undefined;
export interface FilePorts {
  upload: (
    file: File,
    context: { signal: AbortSignal; onProgress: (percent: number) => void },
  ) => Promise<unknown>;
  resolve: (ids: string[], signal: AbortSignal) => Promise<unknown>;
}
export interface FileLimits {
  accept: string;
  maxSize: number;
  maxNumber: number;
}
export interface FileUploadProps {
  ports: FilePorts;
  accept?: string | string[];
  buttonText?: string;
  disabled?: boolean;
  helpText?: string;
  listType?: 'picture' | 'picture-card' | 'text';
  maxNumber?: number;
  maxSize?: number;
  multiple?: boolean;
  showDescription?: boolean;
  showFileList?: boolean;
}
export function fileIds(value: FileValue): string[] {
  if (value === undefined) return [];
  return z
    .array(z.string().min(1))
    .parse(Array.isArray(value) ? value : [value]);
}
export function validateFile(file: File, limits: FileLimits) {
  if (limits.maxSize > 0 && file.size > limits.maxSize * 1024 * 1024)
    throw new RangeError('文件超过大小限制');
  const accepted = limits.accept
    .split(',')
    .map((value) => value.trim().toLowerCase())
    .filter(Boolean);
  const name = file.name.toLowerCase();
  const type = file.type.toLowerCase();
  if (
    accepted.length > 0 &&
    !accepted.some((value) => {
      if (value.startsWith('.')) return name.endsWith(value);
      if (value.endsWith('/*')) return type.startsWith(value.slice(0, -1));
      return type === value;
    })
  )
    throw new TypeError('文件类型不允许');
}
export function parseStoredFile(value: unknown): StoredFile {
  return fileSchema.parse(value);
}
export function parseFileAccess(
  value: unknown,
  requested: string[],
): FileAccess[] {
  const records = z.array(accessSchema).parse(value);
  const ids = new Set(records.map((record) => record.id));
  if (
    ids.size !== records.length ||
    ids.size !== requested.length ||
    requested.some((id) => !ids.has(id))
  )
    throw new TypeError('文件访问结果与请求ID不一致');
  return records.map((record) => {
    const url = new URL(record.url, window.location.origin);
    if (
      !['http:', 'https:'].includes(url.protocol) ||
      url.username ||
      url.password
    )
      throw new TypeError('文件访问地址无效');
    return { ...record, url: url.href };
  });
}
interface UploadJob {
  key: string;
  file: File;
  progress: number;
  controller: AbortController;
}
export class UploadQueue {
  get ids() {
    return this.state.value.ids;
  }
  get jobs() {
    return this.state.value.jobs.map((job) => ({
      key: job.key,
      name: job.file.name,
      progress: job.progress,
    }));
  }
  private disposed = false;
  private state = shallowRef<{ ids: string[]; jobs: UploadJob[] }>({
    ids: [],
    jobs: [],
  });
  constructor(
    private readonly options: {
      ports: () => FilePorts;
      limits: () => FileLimits;
      write: (ids: string[]) => void;
    },
  ) {}
  async add(files: File[]) {
    if (this.disposed)
      throw new DOMException('上传组件已关闭', 'InvalidStateError');
    const limits = this.options.limits();
    if (this.ids.length + this.jobs.length + files.length > limits.maxNumber)
      throw new RangeError('文件数量超过限制');
    for (const file of files) validateFile(file, limits);
    const jobs = files.map((file) => ({
      key: crypto.randomUUID(),
      file,
      progress: 0,
      controller: new AbortController(),
    }));
    this.state.value = {
      ...this.state.value,
      jobs: [...this.state.value.jobs, ...jobs],
    };
    const uploaded: StoredFile[] = [];
    try {
      for (const job of jobs) {
        const { signal } = job.controller;
        if (signal.aborted) continue;
        try {
          const value = await this.options.ports().upload(job.file, {
            signal,
            onProgress: (percent) => {
              if (signal.aborted) return;
              if (!Number.isFinite(percent) || percent < 0 || percent > 100)
                throw new RangeError('上传进度无效');
              this.state.value = {
                ...this.state.value,
                jobs: this.state.value.jobs.map((current) =>
                  current.key === job.key
                    ? { ...current, progress: percent }
                    : current,
                ),
              };
            },
          });
          signal.throwIfAborted();
          const file = parseStoredFile(value);
          this.commit([...new Set([...this.ids, file.id])]);
          uploaded.push(file);
        } catch (error) {
          if (!signal.aborted) throw error;
        } finally {
          this.removeJob(job.key);
        }
      }
      return uploaded;
    } finally {
      for (const job of jobs) {
        job.controller.abort();
        this.removeJob(job.key);
      }
    }
  }
  cancel(key: string) {
    this.state.value.jobs.find((job) => job.key === key)?.controller.abort();
    this.removeJob(key);
  }
  cancelAll() {
    for (const job of this.state.value.jobs) job.controller.abort();
    this.state.value = { ...this.state.value, jobs: [] };
  }
  dispose() {
    this.disposed = true;
    this.cancelAll();
  }
  remove(id: string) {
    this.commit(this.ids.filter((value) => value !== id));
  }
  sync(ids: string[]) {
    if (
      ids.length === this.ids.length &&
      ids.every((id, index) => id === this.ids[index])
    )
      return;
    this.cancelAll();
    this.state.value = { ids: [...ids], jobs: [] };
  }
  private commit(ids: string[]) {
    this.state.value = { ...this.state.value, ids };
    this.options.write([...ids]);
  }
  private removeJob(key: string) {
    this.state.value = {
      ...this.state.value,
      jobs: this.state.value.jobs.filter((job) => job.key !== key),
    };
  }
}
