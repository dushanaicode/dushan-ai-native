import { describe, expect, it, vi } from 'vitest';
import { createApp, h } from 'vue';

import DictTag from '../../dushan-admin-frontend/apps/web-ele/src/components/dict-tag.vue';
import { SessionCoordinator } from '../../dushan-admin-frontend/apps/web-ele/src/services/session/coordinator';

const requests = vi.hoisted(
  () => [] as Array<{ config: unknown; url: string }>,
);
vi.mock('@vben/locales', () => ({ $t: (key: string) => key }));
vi.mock('#/api/request', () => ({
  requestClient: {
    get: (url: string, config: unknown) => {
      requests.push({ config, url });
      // 与后端 DictDataSimpleRespVO 的 camelCase 输出一致，含后端会返回的 null 字段。
      return Promise.resolve([
        {
          colorType: 'success',
          dictType: 'common_status',
          label: '开启',
          permission: null,
          tagStyle: null,
          value: '1',
        },
        {
          colorType: null,
          dictType: 'common_status',
          label: '关闭',
          permission: null,
          tagStyle: null,
          value: '0',
        },
      ]);
    },
  },
}));

const { installDictionary } =
  await import('../../dushan-admin-frontend/apps/web-ele/src/services/dictionary/install');

function sessionFixture() {
  const scope = { generation: 'one', token: 'token' };
  return new SessionCoordinator({
    read: () => scope,
    write: vi.fn(),
    expire: async () => {},
    refresh: async () => 'token',
    lock: (operation) => operation(),
    subscribe: () => () => {},
  });
}

describe('字典运行时装配', () => {
  it('经 installDictionary 装配后 DictTag 可渲染，数据来自后端 simple-list 端点', async () => {
    const session = sessionFixture();
    const element = document.createElement('div');
    const app = createApp(() =>
      h(DictTag, { type: 'common_status', value: [1, 0] }),
    );
    installDictionary(app, session);
    app.mount(element);
    try {
      await vi.waitFor(() => expect(element.textContent).toBe('开启关闭'));
      expect(requests).toEqual([
        {
          config: { signal: expect.any(AbortSignal) },
          url: '/system/dict/data/simple-list',
        },
      ]);
    } finally {
      app.unmount();
      session.dispose();
    }
  });

  it('未装配时 DictTag 仍按约定显式失败，装配缺口不会被静默掩盖', () => {
    const element = document.createElement('div');
    const app = createApp(() =>
      h(DictTag, { type: 'common_status', value: 1 }),
    );
    const errors: unknown[] = [];
    app.config.errorHandler = (error) => {
      errors.push(error);
    };
    app.mount(element);
    try {
      // setup 失败后 Vue 还会上报模板访问未定义运行时的连带错误，只约束首个错误。
      expect(String(errors[0])).toContain('使用字典组件前必须提供');
    } finally {
      app.unmount();
    }
  });
});
