/**
 * 后端分页与通用请求契约。
 *
 * 分页参数为 `page`/`pageSize`（不是旧项目的 pageNo），响应为 `{items,total}`；
 * 所有雪花 ID 在请求与响应中均为十进制字符串。
 */

/** 分页参数（后端 PageQuery：page + pageSize） */
export interface PageParam {
  page?: number;
  pageSize?: number;
}

/** 分页结果（后端 PageResult） */
export interface PageResult<T> {
  items: T[];
  total: number;
}

/** 可导出字段（后端 export-fields 端点） */
export interface ExportField {
  field: string;
  title: string;
}
