import { expect, it, vi } from 'vitest';

import { preferences } from '@vben/preferences';

const startup = vi.hoisted(() => ({
  bootstrap: vi.fn(),
}));

vi.mock('@vben/preferences', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@vben/preferences')>();
  return {
    ...actual,
    initPreferences: async () => {
      // 模拟初始化从已有浏览器缓存恢复的完整用户偏好。
      actual.updatePreferences({
        app: { accessMode: 'frontend', locale: 'en-US' },
      });
    },
  };
});
vi.mock('../../dushan-admin-frontend/apps/web-ele/src/bootstrap', () => ({
  bootstrap: startup.bootstrap,
}));

it('已有偏好不能跳过后端菜单，启动前固定 mixed 并保留用户语言', async () => {
  startup.bootstrap.mockImplementation(async () => ({
    accessMode: preferences.app.accessMode,
    locale: preferences.app.locale,
  }));

  await import('../../dushan-admin-frontend/apps/web-ele/src/main');

  await vi.waitFor(() => expect(startup.bootstrap).toHaveBeenCalledOnce());
  await expect(startup.bootstrap.mock.results[0]?.value).resolves.toEqual({
    accessMode: 'mixed',
    locale: 'en-US',
  });
});
