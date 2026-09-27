import { createApp, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';

import { afterEach, expect, it, vi } from 'vitest';

import QrLoginScan from '../../dushan-admin-frontend/apps/web-ele/src/views/_core/authentication/qr-login-scan.vue';

const api = vi.hoisted(() => ({
  scan: vi.fn(),
  confirm: vi.fn(),
}));

vi.mock('@vben/stores', () => ({
  useUserStore: () => ({ userInfo: { realName: '管理员' } }),
}));
vi.mock('#/store/tenant', () => ({
  useTenantStore: () => ({ currentTenantId: '1' }),
}));
vi.mock('#/api/core/auth', () => ({
  getLoginTenantsApi: async () => ({
    enabled: true,
    tenants: [{ id: '1', name: '渡山无界' }],
  }),
}));
vi.mock('#/api/core/qr-login', () => ({
  isQrLoginEnabled: async () => true,
  scanQrLogin: api.scan,
  confirmQrLogin: api.confirm,
}));
vi.mock('#/api/error-feedback', () => ({ notifyError: vi.fn() }));
vi.mock('#/locales', () => ({
  $t: (key: string, params?: Record<string, string>) =>
    `${key} ${params ? Object.values(params).join(' ') : ''}`.trim(),
}));
vi.mock('element-plus', async () => {
  const { defineComponent, h } = await import('vue');
  const control = (tag: string) =>
    defineComponent({
      setup:
        (_, { attrs, slots }) =>
        () =>
          h(tag, attrs, slots.default?.()),
    });
  return {
    ElButton: control('button'),
    ElCard: control('section'),
    ElMessage: { error: vi.fn() },
  };
});

const cleanups: Array<() => void> = [];
afterEach(() => {
  cleanups.splice(0).forEach((cleanup) => cleanup());
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

async function mountScan(query = '') {
  vi.stubGlobal('isSecureContext', false);
  vi.spyOn(navigator, 'userAgent', 'get').mockReturnValue('iPhone');
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/auth/qr-scan', name: 'QrLoginScan', component: QrLoginScan },
    ],
  });
  const app = createApp(QrLoginScan);
  app.directive('loading', () => {});
  await router.push(`/auth/qr-scan${query}`);
  app.use(router);
  const element = document.createElement('div');
  app.mount(element);
  cleanups.push(() => app.unmount());
  await vi.waitFor(() => expect(element.textContent).toContain('渡山无界'));
  await nextTick();
  return element;
}

it('头像进入 HTTP 扫描入口时显示组织名称与原因，不显示无法使用的蓝色扫描按钮', async () => {
  const element = await mountScan();
  expect(element.querySelector('h1')?.textContent).toBe('qrLogin.scan');
  expect(element.textContent).toContain('qrLogin.organization 渡山无界');
  expect(element.textContent).toContain('qrLogin.httpsRequired');
  expect(element.textContent).toContain('qrLogin.browserSessionHint');
  expect(
    [...element.querySelectorAll('button')].some(
      (button) => button.textContent?.trim() === 'qrLogin.scan',
    ),
  ).toBe(false);
  expect(api.scan).not.toHaveBeenCalled();
});

it('系统相机打开带票据的 HTTP 链接后仍能显示核对码并确认电脑登录', async () => {
  const ticket = 'a'.repeat(43);
  api.scan.mockResolvedValue({
    code: '123456',
    browser: 'Chrome',
    ip: '192.168.1.10',
  });
  api.confirm.mockResolvedValue(undefined);
  const element = await mountScan(`?ticket=${ticket}&tenantId=1`);
  await vi.waitFor(() => expect(element.textContent).toContain('123456'));
  expect(element.querySelector('h1')?.textContent).toBe('qrLogin.scanTitle');
  expect(element.textContent).not.toContain('qrLogin.httpsRequired');
  const confirm = [...element.querySelectorAll('button')].find(
    (button) => button.textContent?.trim() === 'qrLogin.confirm',
  );
  expect(confirm).toBeDefined();
  confirm?.click();
  await vi.waitFor(() =>
    expect(api.confirm).toHaveBeenCalledWith(ticket, true),
  );
  await nextTick();
  expect(element.textContent).toContain('qrLogin.result.approved');
});
