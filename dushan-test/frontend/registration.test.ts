import { createApp, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';

import { initStores } from '@vben/stores';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { coreRoutes } from '../../dushan-admin-frontend/apps/web-ele/src/router/routes/core';
import Login from '../../dushan-admin-frontend/apps/web-ele/src/views/_core/authentication/login.vue';
import Register from '../../dushan-admin-frontend/apps/web-ele/src/views/_core/authentication/register.vue';
import AuthenticationFormView from '../../dushan-admin-frontend/packages/effects/layouts/src/authentication/form.vue';

const stubs = vi.hoisted(() => ({
  backend: false,
  get: vi.fn(),
  register: vi.fn(),
  verify: vi.fn(),
  error: vi.fn(),
  purpose: '',
  schema: [] as any[],
  submit: undefined as ((values: Record<string, unknown>) => void) | undefined,
}));
vi.mock('#/api/request', () => ({
  authenticationClient: { get: stubs.get },
  anonymousClient: { post: vi.fn(), get: async () => [] },
  requestClient: {},
}));
vi.mock('#/store', () => ({
  useAuthStore: () => ({ authRegister: stubs.register, loginLoading: false }),
}));
vi.mock('#/services/captcha/ports', () => ({ createCaptchaPorts: () => ({}) }));
vi.mock('@vben/locales', () => ({ $t: (key: string) => key }));
vi.mock('#/locales', () => ({ $t: (key: string) => key }));
vi.mock('element-plus', () => ({ ElMessage: { error: stubs.error } }));
vi.mock('#/components', async () => {
  const { defineComponent, h } = await import('vue');
  return {
    UnifiedCaptcha: defineComponent({
      props: { purpose: { type: String, required: true } },
      setup(props, { expose }) {
        stubs.purpose = props.purpose;
        expose({ verify: stubs.verify });
        return () => h('div');
      },
    }),
  };
});
vi.mock(
  '../../dushan-admin-frontend/packages/effects/common-ui/src/ui/authentication/register.vue',
  async () => {
    const { defineComponent, h, watchEffect } = await import('vue');
    return {
      default: defineComponent({
        props: {
          formSchema: { type: Array, required: true },
          loading: Boolean,
        },
        emits: ['submit'],
        setup(props, { emit, expose }) {
          watchEffect(() => {
            stubs.schema = props.formSchema;
          });
          stubs.submit = (values) => emit('submit', values);
          expose({ getFormApi: () => ({ setFieldValue: vi.fn() }) });
          return () =>
            h('section', { 'data-registration-form': '' }, 'register');
        },
      }),
    };
  },
);

const cleanups: Array<() => void> = [];
beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  stubs.schema = [];
  stubs.get.mockImplementation(async (url: string) => {
    if (url === '/system/auth/registration-enabled') return stubs.backend;
    if (url === '/system/auth/tenants')
      return {
        enabled: true,
        tenants: [
          { id: '1', name: 'Tenant A' },
          { id: '2', name: 'Tenant B' },
        ],
      };
    throw new Error(`Unexpected endpoint: ${url}`);
  });
  stubs.verify.mockResolvedValue({ verification: 'proof' });
  stubs.register.mockResolvedValue(undefined);
  vi.stubEnv('VITE_APP_TENANT_ENABLE', 'true');
});
afterEach(() => {
  for (const cleanup of cleanups.splice(0)) cleanup();
  vi.unstubAllEnvs();
});

async function mountPage(frontend: boolean, backend: boolean) {
  vi.stubEnv('VITE_APP_REGISTER_ENABLE', String(frontend));
  stubs.backend = backend;
  const registerRoute = coreRoutes
    .find((route) => route.name === 'Authentication')!
    .children!.find((route) => route.name === 'Register')!;
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', redirect: '/auth/login' },
      { path: '/auth/login', name: 'Login', component: Login },
      { ...registerRoute, path: '/auth/register', component: Register },
    ],
  });
  const element = document.createElement('div');
  document.body.append(element);
  const app = createApp(() => h(AuthenticationFormView, { dataSide: 'right' }));
  app.use(router);
  await initStores(app, { namespace: 'registration-test' });
  await router.push('/auth/login');
  await router.isReady();
  app.mount(element);
  cleanups.push(() => {
    app.unmount();
    element.remove();
  });
  await nextTick();
  return { element, router };
}

describe('管理后台注册双开关', () => {
  it('第三方登录关闭时直接回调路由返回登录页', async () => {
    vi.stubEnv('VITE_APP_SOCIAL_LOGIN_ENABLE', 'false');
    const callback = coreRoutes
      .find((route) => route.name === 'Authentication')!
      .children!.find((route) => route.name === 'SocialLogin')!;
    const guard = callback.beforeEnter as () => unknown;
    expect(guard()).toEqual({ path: '/auth/login', replace: true });
    vi.stubEnv('VITE_APP_SOCIAL_LOGIN_ENABLE', 'true');
    expect(guard()).toBe(true);
  });
  it.each([
    [false, false],
    [false, true],
    [true, false],
    [true, true],
  ])(
    '创建账号入口和直接路由一致：前端 %s / 后端 %s',
    async (frontend, backend) => {
      const { element, router } = await mountPage(frontend, backend);
      const enabled = frontend && backend;
      await vi.waitFor(() =>
        expect(
          element.textContent!.includes('authentication.createAccount'),
        ).toBe(enabled),
      );
      await router.push('/auth/register');
      expect(router.currentRoute.value.path).toBe(
        enabled ? '/auth/register' : '/auth/login',
      );
      await vi.waitFor(() =>
        expect(Boolean(element.querySelector('[data-registration-form]'))).toBe(
          enabled,
        ),
      );
      if (!frontend)
        expect(stubs.get).not.toHaveBeenCalledWith(
          '/system/auth/registration-enabled',
        );
    },
  );

  it('双开后提交注册专用验证码和所选租户，等待期间不串入新的表单值', async () => {
    const { router } = await mountPage(true, true);
    await router.push('/auth/register');
    await vi.waitFor(() => expect(stubs.purpose).toBe('register'));
    const pending = Promise.withResolvers<{ verification: string }>();
    stubs.verify.mockReturnValueOnce(pending.promise);
    const values = {
      username: 'newuser',
      nickname: 'New',
      password: 'Password123',
      tenantId: '1',
    };
    stubs.submit!(values);
    await vi.waitFor(() => expect(stubs.verify).toHaveBeenCalledOnce());
    values.tenantId = '2';
    values.username = 'changeduser';
    pending.resolve({ verification: 'register-proof' });
    await vi.waitFor(() =>
      expect(stubs.register).toHaveBeenCalledWith(
        {
          username: 'newuser',
          nickname: 'New',
          password: 'Password123',
          verification: 'register-proof',
        },
        '1',
      ),
    );
    const confirmation = stubs.schema.find(
      (field) => field.fieldName === 'confirmPassword',
    );
    expect(
      confirmation.dependencies
        .resolve({ values })
        .rules.safeParse('OtherPassword').success,
    ).toBe(false);
  });

  it('页面打开后关闭后端开关，再提交也不消费验证码、不调用注册', async () => {
    const { router } = await mountPage(true, true);
    await router.push('/auth/register');
    await vi.waitFor(() => expect(stubs.purpose).toBe('register'));
    stubs.backend = false;
    stubs.submit!({
      username: 'newuser',
      nickname: 'New',
      password: 'Password123',
      tenantId: '1',
    });
    await vi.waitFor(() =>
      expect(stubs.error).toHaveBeenCalledWith('registration.disabled'),
    );
    expect(stubs.verify).not.toHaveBeenCalled();
    expect(stubs.register).not.toHaveBeenCalled();
  });
});
