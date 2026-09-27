import { createApp, h } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';

import { initStores } from '@vben/stores';

import { afterEach, expect, it, vi } from 'vitest';

import CodeLogin from '../../dushan-admin-frontend/apps/web-ele/src/views/_core/authentication/code-login.vue';
import ForgetPassword from '../../dushan-admin-frontend/apps/web-ele/src/views/_core/authentication/forget-password.vue';
import Login from '../../dushan-admin-frontend/apps/web-ele/src/views/_core/authentication/login.vue';
import QrCodeLogin from '../../dushan-admin-frontend/apps/web-ele/src/views/_core/authentication/qrcode-login.vue';
import AuthenticationFormView from '../../dushan-admin-frontend/packages/effects/layouts/src/authentication/form.vue';

const providers = vi.hoisted(() => vi.fn(async () => []));
vi.mock('#/api/core/auth', () => ({
  isRegistrationEnabled: async () => false,
  getSocialProvidersApi: providers,
  getLoginTenantsApi: async () => ({
    enabled: true,
    tenants: [{ id: '1', name: 'A' }],
  }),
  resetPasswordApi: vi.fn(),
  sendLoginSmsApi: vi.fn(),
  sendRecoveryCodeApi: vi.fn(),
}));
vi.mock('#/store', () => ({
  useAuthStore: () => ({ loginLoading: false }),
}));
vi.mock('#/services/captcha/ports', () => ({ createCaptchaPorts: () => ({}) }));
vi.mock('@vben/locales', () => ({ $t: (key: string) => key }));
vi.mock('#/locales', () => ({ $t: (key: string) => key }));
vi.mock('#/api/core/qr-login', () => ({
  isQrLoginEnabled: async () => true,
  createQrLogin: async () => ({
    ticket: 'a'.repeat(43),
    tenantId: '1',
    code: '123456',
    expiresAt: Date.now() + 180000,
    pollInterval: 2000,
  }),
  cancelQrLogin: vi.fn(),
  pollQrLogin: async () => ({ status: 'waiting' }),
}));
vi.mock('@vueuse/integrations/useQRCode', async () => {
  const { ref } = await import('vue');
  return { useQRCode: () => ref('data:image/png;base64,') };
});
vi.mock('element-plus', async () => {
  const { defineComponent, h } = await import('vue');
  const control = (tag: string) =>
    defineComponent({
      inheritAttrs: false,
      setup:
        (_, { attrs, slots }) =>
        () =>
          h(tag, attrs, slots.default?.()),
    });
  return {
    ElMessage: { error: vi.fn() },
    ElButton: control('button'),
    ElSelect: control('select'),
    ElOption: control('option'),
  };
});
vi.mock('#/components', async () => {
  const { defineComponent, h } = await import('vue');
  return {
    UnifiedCaptcha: defineComponent({
      setup: () => () => h('div', { 'data-captcha': '' }),
    }),
  };
});
const cleanups: Array<() => void> = [];
afterEach(() => {
  for (const cleanup of cleanups.splice(0)) cleanup();
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

it('认证页在真实 Transition/KeepAlive 中连续往返，不白屏且保留布局属性与登录缓存', async () => {
  vi.stubEnv('VITE_APP_TENANT_ENABLE', 'true');
  vi.stubEnv('VITE_APP_SOCIAL_LOGIN_ENABLE', 'true');
  localStorage.clear();
  const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', redirect: '/auth/login' },
      { path: '/auth/login', component: Login },
      { path: '/auth/code-login', component: CodeLogin },
      { path: '/auth/qrcode-login', component: QrCodeLogin },
      {
        name: 'QrLoginScan',
        path: '/auth/qr-scan',
        component: { render: () => null },
      },
      { path: '/auth/forget-password', component: ForgetPassword },
    ],
  });
  const element = document.createElement('div');
  document.body.append(element);
  const app = createApp(() => h(AuthenticationFormView, { dataSide: 'right' }));
  app.use(router);
  app.directive('loading', {});
  await initStores(app, { namespace: 'auth-navigation-test' });
  await router.push('/auth/login');
  await router.isReady();
  app.mount(element);
  cleanups.push(() => {
    app.unmount();
    element.remove();
  });
  await vi.waitFor(() =>
    expect(
      element.querySelector('input[placeholder="authentication.usernameTip"]'),
    ).not.toBeNull(),
  );
  const cachedLogin = element.querySelector(
    'input[placeholder="authentication.usernameTip"]',
  );
  await vi.waitFor(() => expect(providers).toHaveBeenCalledOnce());
  const subtitles: Record<string, string> = {
    'code-login': 'authentication.codeSubtitle',
    'forget-password': 'recovery.subtitle',
    login: 'authentication.loginSubtitle',
    'qrcode-login': 'qrLogin.subtitle',
  };

  for (const [page, label] of [
    ['code-login', 'authentication.mobileLogin'],
    ['login', 'common.back'],
    ['qrcode-login', 'authentication.qrcodeLogin'],
    ['login', 'qrLogin.passwordLogin'],
    ['forget-password', 'authentication.forgetPassword'],
    ['login', 'common.back'],
    ['code-login', 'authentication.mobileLogin'],
    ['login', 'common.back'],
    ['forget-password', 'authentication.forgetPassword'],
    ['login', 'common.back'],
  ] as const) {
    const link = [
      ...element.querySelectorAll<HTMLElement>('button, .vben-link'),
    ].find((item) => item.textContent?.trim() === label);
    expect(link, label).toBeDefined();
    link!.click();
    await vi.waitFor(() => {
      expect(router.currentRoute.value.path).toBe(`/auth/${page}`);
      expect(element.querySelectorAll('h1,h2')).toHaveLength(1);
      expect(element.textContent).toContain(subtitles[page]);
      expect(
        element.querySelector('.side-content[data-side="right"] :is(h1,h2)'),
      ).not.toBeNull();
    });
  }
  expect(
    element.querySelector('input[placeholder="authentication.usernameTip"]'),
  ).toBe(cachedLogin);
  expect(warn).not.toHaveBeenCalled();
});
