import { createApp, nextTick } from 'vue';

import { afterEach, beforeEach, expect, it, vi } from 'vitest';

import { BusinessError } from '../../dushan-admin-frontend/apps/web-ele/src/api/business-error';
import SocialLogin from '../../dushan-admin-frontend/apps/web-ele/src/views/_core/authentication/social-login.vue';

const stubs = vi.hoisted(() => ({
  context: {
    type: 20,
    codeParameter: 'code',
    tenantId: '2',
    returnPath: '/workbench',
  } as Record<string, unknown>,
  tenant: { currentTenantId: '2' },
  user: { userId: '501', homePath: '/home' },
  session: { generation: 'current', token: 'token' },
  consume: vi.fn(),
  social: vi.fn(),
  login: vi.fn(),
  bind: vi.fn(),
  begin: vi.fn(),
  replace: vi.fn(),
  info: vi.fn(),
  verify: vi.fn(),
  purpose: '',
  submit: undefined as ((values: Record<string, unknown>) => void) | undefined,
}));
vi.mock('#/store', () => ({
  useAuthStore: () => ({
    authSocialLogin: stubs.social,
    authLogin: stubs.login,
    fetchUserInfo: stubs.info,
  }),
}));
vi.mock('#/store/tenant', () => ({ useTenantStore: () => stubs.tenant }));
vi.mock('@vben/stores', () => ({
  useUserStore: () => ({ userInfo: stubs.user }),
}));
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: { code: 'once-code', state: 'once-state' } }),
  useRouter: () => ({ replace: stubs.replace }),
}));
vi.mock('@vben/locales', () => ({ $t: (key: string) => key }));
vi.mock('#/api/system/social/user', () => ({ bindSocialUser: stubs.bind }));
vi.mock('#/services/session/runtime', () => ({
  getSession: () => ({ capture: () => stubs.session, assertCurrent: vi.fn() }),
}));
vi.mock('#/services/captcha/ports', () => ({ createCaptchaPorts: () => ({}) }));
vi.mock(
  '../../dushan-admin-frontend/apps/web-ele/src/views/_core/authentication/social-oauth',
  async (original) => ({
    ...(await original<object>()),
    consumeSocialContext: stubs.consume,
    beginSocialOAuth: stubs.begin,
  }),
);
vi.mock('#/api/core/auth', () => ({ socialAuthRedirectApi: vi.fn() }));
vi.mock('#/components', async () => {
  const { defineComponent, h } = await import('vue');
  return {
    UnifiedCaptcha: defineComponent({
      props: { purpose: String },
      setup(props, { expose }) {
        stubs.purpose = props.purpose!;
        expose({ verify: stubs.verify });
        return () => h('div');
      },
    }),
  };
});
vi.mock(
  '../../dushan-admin-frontend/packages/effects/common-ui/src/ui/authentication/login.vue',
  async () => {
    const { defineComponent, h } = await import('vue');
    return {
      default: defineComponent({
        emits: ['submit'],
        setup(_, { emit }) {
          stubs.submit = (values) => emit('submit', values);
          return () => h('div', { 'data-binding-form': '' });
        },
      }),
    };
  },
);
const cleanups: Array<() => void> = [];
beforeEach(() => {
  vi.clearAllMocks();
  stubs.context = {
    type: 20,
    codeParameter: 'code',
    tenantId: '2',
    returnPath: '/workbench',
  };
  stubs.tenant.currentTenantId = '2';
  stubs.consume.mockImplementation(() => stubs.context);
  stubs.info.mockResolvedValue(stubs.user);
  stubs.verify.mockResolvedValue({ verification: 'proof' });
  stubs.login.mockImplementation(async (_, __, success) => {
    await success();
  });
  stubs.social.mockImplementation(async (_, success) => {
    await success();
  });
});
afterEach(() => {
  for (const close of cleanups.splice(0)) close();
});
async function mount() {
  const element = document.createElement('div');
  const app = createApp(SocialLogin);
  app.mount(element);
  cleanups.push(() => app.unmount());
  await nextTick();
  return element;
}

it('已绑定回调只调用社交登录，并复用返回路径', async () => {
  await mount();
  await vi.waitFor(() =>
    expect(stubs.replace).toHaveBeenCalledWith('/workbench'),
  );
  expect(stubs.social.mock.calls[0][0]).toEqual({
    type: 20,
    code: 'once-code',
    state: 'once-state',
  });
  expect(stubs.bind).not.toHaveBeenCalled();
});

it('未绑定后验证已有账号，再发起全新授权，不重放旧code/state', async () => {
  stubs.social.mockRejectedValueOnce(
    new BusinessError(
      { code: 1_002_000_005, message: 'not bound', data: null, error: null },
      {},
    ),
  );
  const element = await mount();
  await vi.waitFor(() =>
    expect(element.querySelector('[data-binding-form]')).not.toBeNull(),
  );
  expect(stubs.purpose).toBe('login');
  stubs.submit!({ username: 'admin', password: 'Password123' });
  await vi.waitFor(() =>
    expect(stubs.begin).toHaveBeenCalledWith({
      type: 20,
      codeParameter: 'code',
      tenantId: '2',
      returnPath: '/workbench',
      bindingAccountId: '501',
    }),
  );
  expect(stubs.login.mock.calls[0].slice(0, 2)).toEqual([
    { username: 'admin', password: 'Password123', verification: 'proof' },
    '2',
  ]);
  expect(stubs.bind).not.toHaveBeenCalled();
});

it('绑定回调核对现有账号与租户，并把同一会话代次传给请求', async () => {
  stubs.context.bindingAccountId = '501';
  await mount();
  await vi.waitFor(() =>
    expect(stubs.bind).toHaveBeenCalledWith(
      { type: 20, code: 'once-code', state: 'once-state' },
      stubs.session,
    ),
  );
  expect(stubs.social).not.toHaveBeenCalled();
  expect(stubs.replace).toHaveBeenCalledWith('/workbench');
});

it('绑定期间账号或租户变化时拒绝绑定', async () => {
  stubs.context.bindingAccountId = 'another-account';
  const element = await mount();
  await vi.waitFor(() =>
    expect(element.textContent).toContain('socialLogin.sessionChanged'),
  );
  expect(stubs.bind).not.toHaveBeenCalled();
});

it('没有本标签页的state上下文时不调用后端、不显示绑定表单', async () => {
  stubs.consume.mockImplementation(() => {
    throw new Error('missing context');
  });
  const element = await mount();
  await vi.waitFor(() =>
    expect(element.textContent).toContain('socialLogin.failed'),
  );
  expect(stubs.social).not.toHaveBeenCalled();
  expect(stubs.bind).not.toHaveBeenCalled();
});
