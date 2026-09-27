import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createApp, nextTick } from 'vue';
import { initStores } from '@vben/stores';
import CodeLogin from '../../dushan-admin-frontend/apps/web-ele/src/views/_core/authentication/code-login.vue';

const stubs = vi.hoisted(() => ({
  config: vi.fn(),
  send: vi.fn(),
  login: vi.fn(),
  verify: vi.fn(),
  schema: [] as any[],
  values: {} as Record<string, string>,
  submit: undefined as undefined | ((values: Record<string, string>) => void),
}));
vi.mock('#/api/core/auth', () => ({
  getLoginTenantsApi: stubs.config,
  sendLoginSmsApi: stubs.send,
}));
vi.mock('#/store', () => ({
  useAuthStore: () => ({ authSmsLogin: stubs.login, loginLoading: false }),
}));
vi.mock('#/services/captcha/ports', () => ({ createCaptchaPorts: () => ({}) }));
vi.mock('@vben/locales', () => ({ $t: (key: string) => key }));
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn() },
}));
vi.mock('#/components', async () => {
  const { defineComponent, h } = await import('vue');
  return {
    UnifiedCaptcha: defineComponent({
      setup(_, { expose }) {
        expose({ verify: stubs.verify });
        return () => h('div');
      },
    }),
  };
});
vi.mock(
  '../../dushan-admin-frontend/packages/effects/common-ui/src/ui/authentication/code-login.vue',
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
              setFieldValue: (name: string, value: string) => {
                stubs.values[name] = value;
              },
              getValues: async () => ({ ...stubs.values }),
              validateField: async () => {},
              isFieldValid: async () => true,
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
  const app = createApp(CodeLogin);
  await initStores(app, { namespace: 'sms-login-test' });
  const element = document.createElement('div');
  app.mount(element);
  cleanups.push(() => app.unmount());
  await vi.waitFor(() => expect(stubs.config).toHaveBeenCalled());
  await nextTick();
  await nextTick();
}
beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  vi.stubEnv('VITE_APP_TENANT_ENABLE', 'true');
  stubs.config.mockResolvedValue({
    enabled: true,
    tenants: [{ id: '1', name: 'A' }],
  });
  stubs.send.mockResolvedValue(4);
  stubs.verify.mockResolvedValue({ verification: 'proof' });
  stubs.login.mockResolvedValue(undefined);
  stubs.values = { mobile: '13800001001', code: '8888' };
});
afterEach(() => {
  for (const cleanup of cleanups.splice(0)) cleanup();
  vi.unstubAllEnvs();
});

describe('实际手机号登录页', () => {
  it('人机验证通过后发送，使用服务端验证码长度并清空旧码', async () => {
    stubs.send.mockResolvedValue(6);
    await mountLogin();
    await stubs.schema
      .find((field) => field.fieldName === 'code')
      .componentProps.handleSendCode();
    await nextTick();
    expect(stubs.send).toHaveBeenCalledWith(
      {
        mobile: '13800001001',
        verification: 'proof',
      },
      '1',
    );
    expect(
      stubs.schema.find((field) => field.fieldName === 'code').componentProps
        .codeLength,
    ).toBe(6);
    expect(stubs.values.code).toBe('');
  });
  it('取消人机验证不发送短信', async () => {
    stubs.verify.mockRejectedValue(new Error('cancelled'));
    await mountLogin();
    await expect(
      stubs.schema
        .find((field) => field.fieldName === 'code')
        .componentProps.handleSendCode(),
    ).rejects.toThrow('cancelled');
    expect(stubs.send).not.toHaveBeenCalled();
  });
  it('校验过程中切换手机号或租户不改变本次发送目标', async () => {
    const pending = Promise.withResolvers<{ verification: string }>();
    stubs.verify.mockReturnValue(pending.promise);
    await mountLogin();
    const operation = stubs.schema
      .find((field) => field.fieldName === 'code')
      .componentProps.handleSendCode();
    await vi.waitFor(() => expect(stubs.verify).toHaveBeenCalled());
    stubs.values.mobile = '13800001002';
    stubs.values.tenantId = '2';
    pending.resolve({ verification: 'proof' });
    await operation;
    expect(stubs.send).toHaveBeenCalledWith(
      {
        mobile: '13800001001',
        verification: 'proof',
      },
      '1',
    );
  });
  it('单租户登录不提交历史租户，使用手机号登录入口', async () => {
    stubs.config.mockResolvedValue({ enabled: false, tenants: [] });
    await mountLogin();
    stubs.submit!({ tenantId: '99', mobile: '13800001001', code: '8888' });
    await nextTick();
    expect(stubs.login).toHaveBeenCalledWith(
      {
        mobile: '13800001001',
        code: '8888',
      },
      undefined,
    );
  });
});
