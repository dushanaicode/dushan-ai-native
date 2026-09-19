/**
 * 后端 PermissionDataScopeEnum 数据权限范围（代码常量）。
 * 与 `system_data_scope` 字典值 1-5 对应；DEPT_CUSTOM=2 时需要选择部门集合。
 */
export const DataScope = {
  ALL: 1,
  DEPT_AND_CHILD: 4,
  DEPT_CUSTOM: 2,
  DEPT_ONLY: 3,
  SELF: 5,
} as const;

export type DataScopeValue = (typeof DataScope)[keyof typeof DataScope];
