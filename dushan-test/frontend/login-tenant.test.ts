import { createApp, nextTick } from 'vue';

import { initStores } from '@vben/stores';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useTenantStore } from '../../dushan-admin-frontend/apps/web-ele/src/store/tenant';
import Login from '../../dushan-admin-frontend/apps/web-ele/src/views/_core/authentication/login.vue';

const stubs = vi.hoisted(() => ({
  config: vi.fn(),
  login: vi.fn(),
  schema: [] as any[],
  submit: undefined as ((values: Record<string, unknown>) => void) | undefined,
  values: {} as Record<string, unknown>,
}));

vi.mock('#/api/core/auth', () => ({
  getLoginTenantsApi: stubs.config,
  isRegistrationEnabled: async () => false,
  getSocialProvidersApi: async () => [],
}));
vi.mock('#/store', async () => ({
  useAuthStore: () => ({ authLogin: stubs.login, loginLoading: false }),
  ...(await import('../../dushan-admin-frontend/apps/web-ele/src/store/tenant')),
}));
vi.mock('#/services/captcha/ports', () => ({ createCaptchaPorts: () => ({}) }));
vi.mock('@vben/locales', () => ({ $t: (key: string) => key }));
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn() } }));
vi.mock('#/components', async () => {
  const { defineComponent, h } = await import('vue');
  return {
    UnifiedCaptcha: defineComponent({
      setup(_, { expose }) {
        expose({ verify: async () => undefined });
        return () => h('div');
      },
    }),
  };
});
vi.mock(
  '../../dushan-admin-frontend/packages/effects/common-ui/src/ui/authentication/login.vue',
  async () => {
    const { defineComponent, h, watchEffect } = await import('vue');
    return {
      default: defineComponent({
        props: ['formSchema', 'loading'],
        emits: ['submit'],
        setup(props, { emit, expose }) {
          watchEffect(() => {
            stubs.schema = props.formSchema;
          });
          stubs.submit = (values) => emit('submit', values);
          expose({
            getFormApi: () => ({
              setFieldValue: (key: string, value: string) => {
                stubs.values[key] = value;
              },
            }),
          });
          return () => h('div');
        },
      }),
    };
  },
);

const cleanups: Array<() => void> = [];

async function mountLogin() {
  const element = document.createElement('div');
  document.body.append(element);
  const app = createApp(Login);
  await initStores(app, { namespace: 'login-tenant-test' });
  app.mount(element);
  cleanups.push(() => {
    app.unmount();
    element.remove();
  });
  await vi.waitFor(() => expect(stubs.config).toHaveBeenCalled());
  await nextTick();
  await nextTick();
  return element;
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  stubs.schema = [];
  stubs.values = {};
  stubs.login.mockResolvedValue(undefined);
  vi.stubEnv('VITE_APP_TENANT_ENABLE', 'true');
});

afterEach(() => {
  for (const cleanup of cleanups.splice(0)) cleanup();
  vi.unstubAllEnvs();
});

describe('登录页租户开关与持久化', () => {
  it('保存所选租户，下次挂载预选；实际会话租户不持久化', async () => {
    stubs.config.mockResolvedValue({
      enabled: true,
      tenants: [
        { id: '1', name: 'A' },
        { id: '9223372036854775807', name: 'B' },
      ],
    });
    await mountLogin();
    const tenant = stubs.schema.find((field) => field.fieldName === 'tenantId');
    expect(tenant.componentProps.options).toEqual([
      { label: 'A', value: '1' },
      { label: 'B', value: '9223372036854775807' },
    ]);
    tenant.dependencies.resolve({
      values: { tenantId: '9223372036854775807' },
    });
    useTenantStore().currentTenantId = '1';
    await nextTick();
    expect(
      JSON.parse(localStorage.getItem('login-tenant-test-tenant')!),
    ).toEqual({ lastTenantId: '9223372036854775807' });
    await mountLogin();
    expect(stubs.values.tenantId).toBe('9223372036854775807');
    stubs.submit!({
      username: 'admin',
      password: 'secret',
      tenantId: '9223372036854775807',
    });
    await nextTick();
    expect(stubs.login).toHaveBeenCalledWith(
      {
        username: 'admin',
        password: 'secret',
        verification: undefined,
      },
      '9223372036854775807',
    );
  });

  it.each(['true', 'false'])(
    '后端关闭时无租户字段且忽略历史选择，前端开关=%s',
    async (flag) => {
      vi.stubEnv('VITE_APP_TENANT_ENABLE', flag);
      localStorage.setItem(
        'login-tenant-test-tenant',
        JSON.stringify({ lastTenantId: '99' }),
      );
      stubs.config.mockResolvedValue({ enabled: false, tenants: [] });
      await mountLogin();
      expect(stubs.schema.some((field) => field.fieldName === 'tenantId')).toBe(
        false,
      );
      stubs.submit!({ username: 'admin', password: 'secret', tenantId: '99' });
      await nextTick();
      expect(stubs.login).toHaveBeenCalledWith(
        {
          username: 'admin',
          password: 'secret',
          verification: undefined,
        },
        undefined,
      );
    },
  );

  it('后端开启而前端关闭时明确提示配置问题，禁止错误登录', async () => {
    vi.stubEnv('VITE_APP_TENANT_ENABLE', 'false');
    stubs.config.mockResolvedValue({
      enabled: true,
      tenants: [{ id: '1', name: 'A' }],
    });
    const element = await mountLogin();
    expect(element.textContent).toContain('tenantLogin.configuration');
    stubs.submit!({ username: 'admin', password: 'secret' });
    await nextTick();
    expect(stubs.login).not.toHaveBeenCalled();
  });

  it.each(['empty', 'loadFailed'])(
    '租户列表异常时不回退默认租户：%s',
    async (kind) => {
      if (kind === 'empty')
        stubs.config.mockResolvedValue({ enabled: true, tenants: [] });
      else stubs.config.mockRejectedValue(new Error('offline'));
      const element = await mountLogin();
      expect(element.textContent).toContain(`tenantLogin.${kind}`);
      stubs.submit!({ username: 'admin', password: 'secret' });
      await nextTick();
      expect(stubs.login).not.toHaveBeenCalled();
    },
  );
});
