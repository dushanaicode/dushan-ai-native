import type { VNode } from 'vue';

import { expect, it, vi } from 'vitest';

const renderers = vi.hoisted(
  () =>
    new Map<
      string,
      { renderTableDefault: (options: any, params: any) => VNode }
    >(),
);
vi.mock('@vben/plugins/vxe-table', () => ({
  setupVbenVxeTable: ({ configVxeTable }: any) =>
    configVxeTable({
      setConfig: () => {},
      renderer: {
        add: (name: string, renderer: any) => renderers.set(name, renderer),
      },
    }),
  useVbenVxeGrid: vi.fn(),
}));
vi.mock('#/services/dictionary/context', () => ({
  useDictionary: () => ({ getDictOptions: () => [] }),
}));

await import('../../dushan-admin-frontend/apps/web-ele/src/adapter/vxe-table');
const modules = [
  [
    'infra/job',
    await import('../../dushan-admin-frontend/apps/web-ele/src/views/infra/job/data'),
  ],
  [
    'infra/config',
    await import('../../dushan-admin-frontend/apps/web-ele/src/views/infra/config/data'),
  ],
  [
    'infra/dataSourceConfig',
    await import('../../dushan-admin-frontend/apps/web-ele/src/views/infra/dataSourceConfig/data'),
  ],
  [
    'system/notification/notice',
    await import('../../dushan-admin-frontend/apps/web-ele/src/views/system/notification/notice/data'),
  ],
  [
    'system/tenant',
    await import('../../dushan-admin-frontend/apps/web-ele/src/views/system/tenant/data'),
  ],
  [
    'system/tenantPackage',
    await import('../../dushan-admin-frontend/apps/web-ele/src/views/system/tenantPackage/data'),
  ],
  [
    'system/oauth2/client',
    await import('../../dushan-admin-frontend/apps/web-ele/src/views/system/oauth2/client/data'),
  ],
  [
    'system/sms/channel',
    await import('../../dushan-admin-frontend/apps/web-ele/src/views/system/sms/channel/data'),
  ],
  [
    'system/sms/template',
    await import('../../dushan-admin-frontend/apps/web-ele/src/views/system/sms/template/data'),
  ],
  [
    'system/mail/template',
    await import('../../dushan-admin-frontend/apps/web-ele/src/views/system/mail/template/data'),
  ],
  [
    'system/social/client',
    await import('../../dushan-admin-frontend/apps/web-ele/src/views/system/social/client/data'),
  ],
] as const;

const updateCodes: Record<string, string> = {
  'infra/job': 'infra:job:update',
  'infra/config': 'infra:config:type:update',
  'infra/dataSourceConfig': 'infra:data-source:update',
  'system/notification/notice': 'system:notification:update',
  'system/tenant': 'system:tenant:update',
  'system/tenantPackage': 'system:tenant:package:update',
  'system/oauth2/client': 'system:oauth2:client:update',
  'system/sms/channel': 'system:sms:channel:update',
  'system/sms/template': 'system:sms:template:update',
  'system/mail/template': 'system:mail:template:update',
  'system/social/client': 'system:social:client:update',
};

for (const [name, module] of modules) {
  it(`${name} 的实际Schema和Vxe渲染器传递状态及原始行`, async () => {
    const change = vi.fn(async () => true);
    const columns =
      'useGridColumns' in module
        ? name === 'system/tenant' || name === 'system/mail/template'
          ? module.useGridColumns(undefined, change)
          : module.useGridColumns(change)
        : module.useTypeGridColumns(change);
    const column = columns!.find((item) => item.field === 'status')!;
    const row = { id: '10300000050001', status: 1 };
    const vnode = renderers
      .get('CellSwitch')!
      .renderTableDefault(column.cellRender, { column, row });
    const next = name === 'infra/job' ? 2 : 0;
    await expect(vnode.props!.change(next)).resolves.toBe(true);
    expect(change).toHaveBeenCalledExactlyOnceWith(next, row);
    if (name === 'infra/job') expect(vnode.props!.inactiveValue).toBe(2);
    expect(vnode.props!.auth).toEqual([updateCodes[name]]);
  });
}
