import { expect, it } from 'vitest';

import { useCodegenColumnTableColumns } from '../../dushan-admin-frontend/apps/web-ele/src/views/infra/codegen/data';

it.each(['date', 'time', 'datetime'])(
  '代码生成编辑页可以选择与后端一致的 %s 字段类型',
  (fieldType) => {
    expect(useCodegenColumnTableColumns()).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          field: 'fieldType',
          params: {
            options: expect.arrayContaining([
              { label: fieldType, value: fieldType },
            ]),
          },
        }),
      ]),
    );
  },
);
