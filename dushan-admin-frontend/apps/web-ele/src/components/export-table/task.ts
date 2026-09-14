import { shallowRef } from 'vue';

import { downloadFileFromBlob } from '@vben/utils';

export interface ExportColumn {
  field?: string;
  title?: string;
  type?: string;
  slots?: unknown;
}
export interface ExportTableData {
  columns: ExportColumn[];
  fileName: string;
  searchParams?: Record<string, unknown>;
  exportApi: (
    params: Record<string, unknown>,
    signal: AbortSignal,
  ) => Promise<Blob>;
}
export function exportColumns(columns: ExportColumn[]) {
  return columns.filter(
    (column): column is ExportColumn & { field: string; title: string } =>
      column.type !== 'checkbox' &&
      !column.slots &&
      column.field !== undefined &&
      column.title !== undefined,
  );
}
export class ExportTask {
  get loading() {
    return this.state.value;
  }
  private controller: AbortController | undefined;
  private state = shallowRef(false);
  constructor(
    private readonly save: typeof downloadFileFromBlob = downloadFileFromBlob,
  ) {}
  cancel() {
    this.controller?.abort();
    this.controller = undefined;
    this.state.value = false;
  }
  async run(data: ExportTableData, fields: string[]) {
    if (this.loading)
      throw new DOMException('导出正在进行', 'InvalidStateError');
    const allowed = new Set(
      exportColumns(data.columns).map((column) => column.field),
    );
    if (
      !data.fileName ||
      fields.length === 0 ||
      fields.some((field) => !allowed.has(field))
    )
      throw new TypeError('导出文件名或字段无效');
    const controller = new AbortController();
    this.controller = controller;
    this.state.value = true;
    try {
      // exportApi须使用已配置Native拦截器的下载入口，JSON错误在响应边界识别。
      const source = await data.exportApi(
        { ...data.searchParams, fields: [...fields] },
        controller.signal,
      );
      controller.signal.throwIfAborted();
      this.save({ fileName: data.fileName, source });
    } catch (error) {
      controller.signal.throwIfAborted();
      throw error;
    } finally {
      if (this.controller === controller) {
        this.controller = undefined;
        this.state.value = false;
      }
    }
  }
}
