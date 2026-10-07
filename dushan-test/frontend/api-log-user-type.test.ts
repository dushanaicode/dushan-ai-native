import { assert, expect, it, vi } from 'vitest';

import * as accessLog from '../../dushan-admin-frontend/apps/web-ele/src/views/infra/apiAccessLog/data';
import * as errorLog from '../../dushan-admin-frontend/apps/web-ele/src/views/infra/apiErrorLog/data';

vi.mock('@vben/common-ui', () => ({ JsonViewer: { render: () => null } }));
vi.mock('#/components', () => ({
  DictTag: { name: 'DictTag', render: () => null },
}));
vi.mock('#/services/dictionary/context', () => ({ useDictionary: () => ({}) }));
vi.mock('#/utils/range-picker', () => ({
  getRangePickerDefaultProps: () => ({}),
}));

it.each([
  ['访问日志', accessLog],
  ['错误日志', errorLog],
] as const)(
  '%s 列表和详情将匿名类型 0 显示为 -，已登录类型继续使用字典',
  (_, page) => {
    const columns = page.useGridColumns();
    assert(columns);
    const column = columns.find((item) => item.field === 'userType');
    const field = page
      .useDetailSchema()
      .find((item) => item.field === 'userType');
    assert(typeof column?.slots?.default === 'function');
    assert(typeof field?.content === 'function');
    const renderCell = column.slots.default as (params: {
      row: { userType: number };
    }) => unknown;
    const content = field.content as (data: { userType: number }) => unknown;
    expect(renderCell({ row: { userType: 0 } })).toBe('-');
    expect(content({ userType: 0 })).toBe('-');
    expect(renderCell({ row: { userType: 2 } })).toMatchObject({
      props: { type: 'user_type', value: 2 },
    });
    expect(content({ userType: 2 })).toMatchObject({
      props: { type: 'user_type', value: 2 },
    });
  },
);
