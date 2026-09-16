import { describe, expect, it, vi } from 'vitest';
import { createApp, ref } from 'vue';

import { provideDictionary } from '../../dushan-admin-frontend/apps/web-ele/src/services/dictionary/context';
import { DictionaryRuntime } from '../../dushan-admin-frontend/apps/web-ele/src/services/dictionary/runtime';
import { SessionCoordinator } from '../../dushan-admin-frontend/apps/web-ele/src/services/session/coordinator';
import '../../dushan-admin-frontend/apps/web-ele/src/adapter/vxe-table';

const renderers = vi.hoisted(() => new Map<string, any>());
vi.mock('@vben/locales', () => ({ $t: (key: string) => key }));
vi.mock('#/adapter/form', () => ({ useVbenForm: vi.fn() }));
vi.mock('@vben/plugins/vxe-table', () => ({
  setupVbenVxeTable: ({ configVxeTable }: any) =>
    configVxeTable({
      setConfig: vi.fn(),
      renderer: {
        add: (name: string, renderer: unknown) => renderers.set(name, renderer),
      },
    }),
  useVbenVxeGrid: vi.fn(),
}));

describe('实际应用 CellDict 注册', () => {
  it('渲染配置正确传递 type 和行字段，多个值及缺项都有可见结果', async () => {
    const scope = { generation: 'one', token: null };
    const session = new SessionCoordinator({
      read: () => scope,
      write: vi.fn(),
      expire: async () => {},
      refresh: async () => '',
      lock: (operation) => operation(),
      subscribe: () => () => {},
    });
    const dictionary = new DictionaryRuntime({
      session,
      locale: ref('zh-CN'),
      loader: async () => [{ dictType: 'state', value: '0', label: '关闭' }],
    });
    const renderer = renderers.get('CellDict');
    const element = document.createElement('div');
    const app = createApp(() =>
      renderer.renderTableDefault(
        { props: { type: 'state' } },
        { row: { state: [0, 'missing'] }, column: { field: 'state' } },
      ),
    );
    provideDictionary(app, dictionary);
    app.mount(element);
    try {
      await vi.waitFor(() => expect(element.textContent).toBe('关闭missing'));
      expect(element.querySelectorAll('.el-tag')).toHaveLength(2);
    } finally {
      app.unmount();
      session.dispose();
    }
  });
});
