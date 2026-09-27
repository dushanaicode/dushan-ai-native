import { afterEach, expect, it, vi } from 'vitest';
import {
  createApp,
  h,
  nextTick,
  ref,
  resolveDirective,
  withDirectives,
} from 'vue';

import { BusinessError } from '../../dushan-admin-frontend/apps/web-ele/src/api/business-error';
import ServerPage from '../../dushan-admin-frontend/apps/web-ele/src/views/infra/server/index.vue';
import { registerLoadingDirective } from '../../dushan-admin-frontend/packages/effects/common-ui/src/components/loading/index';

const api = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock('#/api/infra/server', () => ({ getServerInfo: api.get }));
vi.mock('@vben/icons', async (original) => ({
  ...(await original<Record<string, unknown>>()),
  IconifyIcon: () => null,
}));
const cleanups: Array<() => void> = [];
afterEach(() => {
  for (const cleanup of cleanups.splice(0)) cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

it('Vben加载指令保留原有子节点，切换状态和卸载正常', async () => {
  vi.useFakeTimers();
  const loading = ref(true);
  const app = createApp({
    setup() {
      const directive = resolveDirective('loading')!;
      return () =>
        withDirectives(h('div', [h('button', '原有内容')]), [
          [directive, loading.value],
        ]);
    },
  });
  registerLoadingDirective(app);
  const element = document.createElement('div');
  document.body.append(element);
  app.mount(element);
  cleanups.push(() => {
    app.unmount();
    element.remove();
  });
  await vi.advanceTimersByTimeAsync(80);
  const button = element.querySelector('button');
  expect(button?.textContent).toBe('原有内容');
  const overlay = element.querySelector('.dot')!.parentElement!;
  expect(overlay.classList.contains('invisible')).toBe(false);
  loading.value = false;
  await nextTick();
  expect(overlay.classList.contains('invisible')).toBe(true);
  expect(element.querySelector('button')).toBe(button);
});

it('服务监控首次显示Vben加载，手动刷新保留内容，后台轮询不遮罩', async () => {
  vi.useFakeTimers();
  const first = Promise.withResolvers<unknown>();
  const manual = Promise.withResolvers<unknown>();
  const polling = Promise.withResolvers<unknown>();
  api.get
    .mockReset()
    .mockReturnValueOnce(first.promise)
    .mockReturnValueOnce(manual.promise)
    .mockReturnValueOnce(polling.promise);
  const app = createApp(ServerPage);
  const element = document.createElement('div');
  document.body.append(element);
  app.mount(element);
  cleanups.push(() => {
    app.unmount();
    element.remove();
  });
  await vi.advanceTimersByTimeAsync(80);
  expect(element.querySelector('.el-skeleton')).toBeNull();
  expect(element.querySelector('.dot')).not.toBeNull();
  expect(element.textContent).not.toContain('CPU');
  const data = {
    cpu: { cpuNum: 4, used: 12, sys: 4, free: 84 },
    mem: {},
    py: {},
    sys: { computerName: 'loading-fixture' },
    sysFiles: [],
  };
  first.resolve(data);
  await vi.advanceTimersByTimeAsync(1);
  expect(element.textContent).toContain('loading-fixture');
  const overlay = element.querySelector('.dot')!.parentElement!;
  expect(overlay.classList.contains('invisible')).toBe(true);
  element.querySelector<HTMLButtonElement>('button')!.click();
  await vi.advanceTimersByTimeAsync(80);
  expect(element.textContent).toContain('loading-fixture');
  expect(overlay.classList.contains('invisible')).toBe(false);
  manual.resolve(data);
  await vi.advanceTimersByTimeAsync(1);
  await vi.advanceTimersByTimeAsync(30000);
  expect(api.get).toHaveBeenCalledTimes(3);
  expect(overlay.classList.contains('invisible')).toBe(true);
  polling.resolve(data);
  await vi.advanceTimersByTimeAsync(1);
  api.get.mockRejectedValueOnce(
    new BusinessError(
      { code: 500, message: '监控暂时不可用', data: null, error: null },
      {},
    ),
  );
  element.querySelector<HTMLButtonElement>('button')!.click();
  await vi.advanceTimersByTimeAsync(80);
  expect(overlay.classList.contains('invisible')).toBe(true);
  expect(element.textContent).toContain('loading-fixture');
  expect(element.textContent).toContain('监控暂时不可用');
});
