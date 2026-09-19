import type {
  DeptNode,
  UserSelectPorts,
} from '#/components/user-select/selection';

import { getSimpleDeptList } from '#/api/system/dept';
import { getUser, getUserPage } from '#/api/system/user';

function buildDeptTree(
  list: { id: string; name: string; parentId: string }[],
): DeptNode[] {
  const nodes = new Map<string, DeptNode>();
  const roots: DeptNode[] = [];
  for (const item of list)
    nodes.set(item.id, { children: [], label: item.name, value: item.id });
  for (const item of list) {
    const node = nodes.get(item.id);
    const parent = nodes.get(item.parentId);
    if (item.parentId !== '0' && parent && node) parent.children.push(node);
    else if (node) roots.push(node);
  }
  return roots;
}

/** UserSelect 组件的后端端口：部门树、分页用户、已选用户。 */
export function createUserSelectPorts(): UserSelectPorts {
  return {
    departments: async (signal) => {
      const list = await getSimpleDeptList();
      if (signal.aborted) throw new DOMException('已取消', 'AbortError');
      return buildDeptTree(
        list.map((item) => ({
          id: item.id ?? '',
          name: item.name ?? '',
          parentId: item.parentId ?? '0',
        })),
      );
    },
    users: async (query, signal) => {
      const page = await getUserPage({
        deptId: query.deptId,
        page: query.page,
        pageSize: query.pageSize,
        username: query.keyword || undefined,
      });
      if (signal.aborted) throw new DOMException('已取消', 'AbortError');
      return {
        items: page.items.map((user) => ({
          description: user.deptName ?? '',
          id: user.id,
          label: user.nickname,
        })),
        total: page.total,
      };
    },
    selected: async (ids, signal) => {
      const users = await Promise.all(ids.map((id) => getUser(id)));
      if (signal.aborted) throw new DOMException('已取消', 'AbortError');
      return users
        .filter((user): user is NonNullable<typeof user> => user !== null)
        .map((user) => ({
          description: user.deptName ?? '',
          id: user.id,
          label: user.nickname,
        }));
    },
  };
}
