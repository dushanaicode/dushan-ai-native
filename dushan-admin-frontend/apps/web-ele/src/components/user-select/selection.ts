import { z } from '@vben/common-ui';

const idSchema = z.string().min(1);
const userSchema = z
  .object({
    id: idSchema,
    label: z.string(),
    description: z.string().optional(),
  })
  .strict();
export type UserRecord = z.infer<typeof userSchema>;
export type UserValue = string | string[] | undefined;
export interface DeptNode {
  value: string;
  label: string;
  children: DeptNode[];
}
const deptSchema: z.ZodType<DeptNode> = z.lazy(() =>
  z
    .object({
      value: idSchema,
      label: z.string(),
      children: z.array(deptSchema),
    })
    .strict(),
);
export interface UserSelectPorts {
  departments: (signal: AbortSignal) => Promise<unknown>;
  users: (
    query: { deptId?: string; keyword: string; page: number; pageSize: number },
    signal: AbortSignal,
  ) => Promise<unknown>;
  selected: (ids: string[], signal: AbortSignal) => Promise<unknown>;
}
export interface UserSelectProps {
  ports: UserSelectPorts;
  deptId?: string;
  disabled?: boolean;
  multiple?: boolean;
  placeholder?: string;
  showDeptFilter?: boolean;
  size?: 'default' | 'large' | 'small';
}
export function userIds(value: UserValue): string[] {
  const ids =
    value === undefined
      ? []
      : z.array(idSchema).parse(Array.isArray(value) ? value : [value]);
  if (new Set(ids).size !== ids.length) throw new TypeError('选择值包含重复ID');
  return ids;
}
export function selectionValue(ids: string[], multiple: boolean): UserValue {
  return multiple ? [...ids] : ids[0];
}
export function toggleUser(ids: string[], id: string, multiple: boolean) {
  if (!multiple) return [id];
  return ids.includes(id) ? ids.filter((value) => value !== id) : [...ids, id];
}
export function parseUsers(value: unknown) {
  const page = z
    .object({
      items: z.array(userSchema),
      total: z.number().int().nonnegative(),
    })
    .strict()
    .parse(value);
  if (new Set(page.items.map((user) => user.id)).size !== page.items.length)
    throw new TypeError('用户列表包含重复ID');
  return page;
}
export function parseSelected(value: unknown, ids: string[]) {
  const users = z.array(userSchema).parse(value);
  const received = new Set(users.map((user) => user.id));
  if (
    received.size !== users.length ||
    received.size !== ids.length ||
    ids.some((id) => !received.has(id))
  )
    throw new TypeError('所选用户结果不完整');
  return users;
}
export function parseDepartments(value: unknown) {
  return z.array(deptSchema).parse(value);
}
