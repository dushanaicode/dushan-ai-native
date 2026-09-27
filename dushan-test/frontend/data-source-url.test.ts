import { createApp, h, nextTick, ref } from 'vue';
import { expect, it, vi } from 'vitest';

import DataSourceUrl from '../../dushan-admin-frontend/apps/web-ele/src/components/data-source-url/data-source-url.vue';

it('只回填脱敏记录的数据库类型时，不生成新连接或覆盖原凭据', async () => {
  const type = ref('mysql');
  const updates = vi.fn();
  const container = document.createElement('div');
  const app = createApp(() =>
    h(DataSourceUrl, { dbType: type.value, 'onUpdate:modelValue': updates }),
  );
  app.mount(container);
  try {
    await nextTick();
    type.value = 'tidb';
    await nextTick();
    await nextTick();
    expect(container.querySelector('.el-select')!.textContent).toContain(
      'TiDB',
    );
    expect(updates).not.toHaveBeenCalled();
  } finally {
    app.unmount();
  }
});

it('回填URL不重写密码、用户名或附加参数，编辑主机保留附加参数', async () => {
  const initial =
    'mysql+aiomysql://user%40test:p%40ss@127.0.0.1:3306/demo?charset=utf8mb4&connect_timeout=7';
  const value = ref(initial);
  const updates = vi.fn((url: string) => {
    value.value = url;
  });
  const container = document.createElement('div');
  const app = createApp(() =>
    h(DataSourceUrl, {
      modelValue: value.value,
      'onUpdate:modelValue': updates,
    }),
  );
  app.mount(container);
  try {
    await nextTick();
    await nextTick();
    expect(updates).not.toHaveBeenCalled();
    expect(
      container.querySelector<HTMLInputElement>(
        'input[placeholder="请输入用户名"]',
      )!.value,
    ).toBe('user@test');
    expect(
      container.querySelector<HTMLInputElement>(
        'input[placeholder="请输入密码"]',
      )!.value,
    ).toBe('p@ss');
    const host = container.querySelector<HTMLInputElement>(
      'input[placeholder="请输入主机地址"]',
    )!;
    host.value = 'db.internal';
    host.dispatchEvent(new Event('input', { bubbles: true }));
    await nextTick();
    await nextTick();
    expect(value.value).toBe(initial.replace('127.0.0.1', 'db.internal'));
  } finally {
    app.unmount();
  }
});

it('手动输入与清空以原始URL为准，不被生成器覆盖或留下旧密码', async () => {
  const value = ref('');
  const updates = vi.fn((url: string) => {
    value.value = url;
  });
  const container = document.createElement('div');
  const app = createApp(() =>
    h(DataSourceUrl, {
      modelValue: value.value,
      'onUpdate:modelValue': updates,
    }),
  );
  app.mount(container);
  try {
    const input = container.querySelector<HTMLTextAreaElement>('textarea')!;
    const manual =
      'postgresql+asyncpg://alice:abc%23def@db:5432/data?command_timeout=9';
    input.value = manual;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    await nextTick();
    await nextTick();
    expect(value.value).toBe(manual);
    expect(input.value).toBe(manual);
    value.value = '';
    await nextTick();
    await nextTick();
    expect(input.value).toBe('');
    expect(
      container.querySelector<HTMLInputElement>(
        'input[placeholder="请输入密码"]',
      )!.value,
    ).toBe('');
  } finally {
    app.unmount();
  }
});
