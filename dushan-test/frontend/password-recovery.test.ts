import { createApp, nextTick } from 'vue';

import { initStores } from '@vben/stores';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import Recovery from '../../dushan-admin-frontend/apps/web-ele/src/views/_core/authentication/forget-password.vue';

const stubs = vi.hoisted(() => ({
  config: vi.fn(),
  send: vi.fn(),
  reset: vi.fn(),
  verify: vi.fn(),
  replace: vi.fn(),
  schema: [] as any[],
  values: {} as Record<string, string>,
  submit: undefined as ((values: Record<string, string>) => void) | undefined,
  purpose: '',
}));
vi.mock('#/api/core/auth', () => ({
  getLoginTenantsApi: stubs.config,
  sendRecoveryCodeApi: stubs.send,
  resetPasswordApi: stubs.reset,
}));
vi.mock('vue-router', () => ({
  useRouter: () => ({ replace: stubs.replace }),
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
      props: ['purpose'],
      setup(props, { expose }) {
        stubs.purpose = props.purpose;
        expose({ verify: stubs.verify });
        return () => h('div');
      },
    }),
  };
});
vi.mock(
  '../../dushan-admin-frontend/packages/effects/common-ui/src/ui/authentication/forget-password.vue',
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
async function mountPage() {
  const app = createApp(Recovery);
  await initStores(app, { namespace: 'recovery-test' });
  app.mount(document.createElement('div'));
  cleanups.push(() => app.unmount());
  await vi.waitFor(() => expect(stubs.config).toHaveBeenCalled());
  await nextTick();
  await nextTick();
}
function field(name: string) {
  return stubs.schema.find((entry) => entry.fieldName === name);
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
  stubs.reset.mockResolvedValue(true);
  stubs.verify.mockResolvedValue({ verification: 'proof' });
  stubs.values = {
    channel: 'sms',
    mobile: '13800001001',
    code: '1234',
    password: 'Changed123',
    confirmPassword: 'Changed123',
  };
});
afterEach(() => {
  for (const close of cleanups.splice(0)) close();
  vi.unstubAllEnvs();
});

describe('实际忘记密码页面', () => {
  it('默认手机号，并使用找回密码专用人机验证用途', async () => {
    await mountPage();
    expect(field('channel').rules.parse(undefined)).toBe('sms');
    expect(field('mobile')).toBeDefined();
    expect(field('email')).toBeUndefined();
    expect(stubs.purpose).toBe('password_reset');
    await field('code').componentProps.handleSendCode();
    expect(stubs.send).toHaveBeenCalledWith(
      {
        channel: 'sms',
        mobile: '13800001001',
        verification: 'proof',
      },
      '1',
    );
  });
  it('切换邮箱清掉旧验证码，发送目标不会夹带手机号', async () => {
    await mountPage();
    stubs.values.channel = 'email';
    stubs.values.email = 'user@example.com';
    field('channel').dependencies.resolve({
      values: stubs.values,
      actions: {
        setFieldValue: (name: string, value: string) => {
          stubs.values[name] = value;
        },
      },
    });
    await nextTick();
    expect(field('email')).toBeDefined();
    expect(field('mobile')).toBeUndefined();
    expect(stubs.values.code).toBe('');
    stubs.send.mockResolvedValue(6);
    await field('code').componentProps.handleSendCode();
    expect(stubs.send).toHaveBeenCalledWith(
      {
        channel: 'email',
        email: 'user@example.com',
        verification: 'proof',
      },
      '1',
    );
    expect(field('code').componentProps.codeLength).toBe(6);
  });
  it('确认密码校验一致，成功重置后返回登录页', async () => {
    await mountPage();
    expect(
      field('confirmPassword')
        .dependencies.resolve({ values: { password: 'Changed123' } })
        .rules.safeParse('Other123').success,
    ).toBe(false);
    stubs.submit!({ ...stubs.values, tenantId: '1' });
    await vi.waitFor(() =>
      expect(stubs.replace).toHaveBeenCalledWith('/auth/login'),
    );
    expect(stubs.reset).toHaveBeenCalledWith(
      {
        channel: 'sms',
        mobile: '13800001001',
        code: '1234',
        password: 'Changed123',
      },
      '1',
    );
  });
  it('取消验证码不发送，单租户不提交历史租户标识', async () => {
    stubs.config.mockResolvedValue({ enabled: false, tenants: [] });
    await mountPage();
    stubs.values.tenantId = '99';
    stubs.verify.mockRejectedValueOnce(new Error('cancelled'));
    await expect(field('code').componentProps.handleSendCode()).rejects.toThrow(
      'cancelled',
    );
    expect(stubs.send).not.toHaveBeenCalled();
    await field('code').componentProps.handleSendCode();
    expect(stubs.send).toHaveBeenCalledWith(
      {
        channel: 'sms',
        mobile: '13800001001',
        verification: 'proof',
      },
      undefined,
    );
  });
});
