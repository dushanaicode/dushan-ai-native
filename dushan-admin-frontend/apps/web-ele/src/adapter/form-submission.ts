import type { NativeRequestConfig } from '../api/response';

import { cloneDeep, get, isEqual } from '@vben/utils';

import { BusinessError } from '../api/business-error';

export interface FormErrorTarget {
  isMounted: boolean;
  form?: unknown;
  getRawValues(): Promise<Record<string, unknown>>;
  getFieldComponentRef(field: string): unknown;
  setFieldError(field: string, message?: string): Promise<void>;
  scrollToFirstError(field: string): void;
}

export type FormSubmitResult<T> =
  | { data: T; status: 'success' }
  | { status: 'error' | 'stale' };

/** 每个表单独立持有服务端错误与提交序号，迟到响应不会污染其他表单。 */
export class FormSubmission {
  private previousFields = new Set<string>();
  private revision = 0;

  constructor(
    private readonly form: FormErrorTarget,
    private readonly notify: (message: string) => void,
  ) {}

  /** 执行请求并映射公开错误；调用方仅在status为success时关闭表单或刷新列表。 */
  async submit<T>(
    request: (config: NativeRequestConfig) => Promise<T>,
    { showSummary = false }: { showSummary?: boolean } = {},
  ): Promise<FormSubmitResult<T>> {
    if (!this.form.isMounted) throw new Error('请在表单挂载后提交请求');
    const revision = ++this.revision;
    const context = this.form.form;
    const current = () =>
      this.form.isMounted &&
      this.form.form === context &&
      revision === this.revision;
    const submitted = cloneDeep(await this.form.getRawValues());
    if (!current()) return { status: 'stale' };
    for (const field of this.previousFields) {
      if (!current()) return { status: 'stale' };
      await this.form.setFieldError(field);
    }
    this.previousFields.clear();
    try {
      const data = await request({ errorMessageMode: 'form' });
      return current() ? { data, status: 'success' } : { status: 'stale' };
    } catch (error) {
      // 网络故障由请求层提示并继续传播，程序错误也不能静默变成普通校验失败。
      if (!(error instanceof BusinessError)) throw error;
      if (!current()) return { status: 'stale' };
      const fields = error.details?.fields ?? [];
      if (fields.length === 0) {
        this.notify(error.message);
        return { status: 'error' };
      }
      const values = await this.form.getRawValues();
      if (!current()) return { status: 'stale' };
      const messages = new Map<string, Set<string>>();
      const unmatched = new Set<string>();
      for (const item of fields) {
        if (!isEqual(get(values, item.field), get(submitted, item.field)))
          continue;
        if (!item.field || !this.form.getFieldComponentRef(item.field)) {
          unmatched.add(item.message);
          continue;
        }
        const group = messages.get(item.field) ?? new Set<string>();
        group.add(item.message);
        messages.set(item.field, group);
      }
      for (const [field, group] of messages) {
        if (!current()) return { status: 'stale' };
        await this.form.setFieldError(field, [...group].join('；'));
        this.previousFields.add(field);
      }
      const first = messages.keys().next().value;
      if (first) this.form.scrollToFirstError(first);
      if (unmatched.size > 0)
        this.notify([error.message, ...unmatched].join('；'));
      else if (showSummary && messages.size > 0) this.notify(error.message);
      return { status: 'error' };
    }
  }
}
