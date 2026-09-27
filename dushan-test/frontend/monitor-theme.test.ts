import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { runInNewContext } from 'node:vm';

import { afterEach, expect, it, vi } from 'vitest';

const source = readFileSync(
  resolve(process.cwd(), '../docker/monitor/ui.js'),
  'utf8',
);

afterEach(() => {
  localStorage.removeItem('jaeger-ui-theme');
  localStorage.removeItem('jaeger-test-other');
});

function configure(
  search: string,
  storage: Pick<Storage, 'setItem'> = localStorage,
) {
  const warn = vi.fn();
  const config = runInNewContext(`${source}\nUIConfig();`, {
    URLSearchParams,
    window: { location: { search }, localStorage: storage },
    console: { warn },
  });
  return { config, warn };
}

it.each(['dark', 'light'])(
  'Native传入%s时覆盖已有Jaeger主题，保留其他偏好',
  (theme) => {
    const previous = theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('jaeger-ui-theme', JSON.stringify(previous));
    localStorage.setItem('jaeger-test-other', 'unchanged');
    const { config } = configure(`?nativeTheme=${theme}`);
    expect(config.themes.enabled).toBe(true);
    expect(localStorage.getItem('jaeger-ui-theme')).toBe(JSON.stringify(theme));
    expect(localStorage.getItem('jaeger-test-other')).toBe('unchanged');
  },
);

it.each(['', '?nativeTheme=invalid'])(
  '没有有效宿主主题参数时保留独立窗口偏好：%s',
  (search) => {
    localStorage.setItem('jaeger-ui-theme', '"light"');
    configure(search);
    expect(localStorage.getItem('jaeger-ui-theme')).toBe('"light"');
  },
);

it('浏览器禁止存储时仍能启动Jaeger界面并记录原因', () => {
  const blocked = new DOMException('Storage blocked', 'SecurityError');
  const storage = {
    setItem() {
      throw blocked;
    },
  };
  const { config, warn } = configure('?nativeTheme=dark', storage);
  expect(config.themes.enabled).toBe(true);
  expect(warn).toHaveBeenCalledWith('Jaeger主题偏好无法保存：', blocked);
});
