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
