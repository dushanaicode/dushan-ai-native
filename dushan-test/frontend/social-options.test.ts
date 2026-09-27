import { createApp, h, nextTick, reactive } from 'vue';

import { afterEach, beforeEach, expect, it, vi } from 'vitest';

import SocialLoginOptions from '../../dushan-admin-frontend/apps/web-ele/src/views/_core/authentication/social-login-options.vue';

const stubs = vi.hoisted(() => ({ providers: vi.fn(), begin: vi.fn() }));
vi.mock('#/api/core/auth', () => ({ getSocialProvidersApi: stubs.providers }));
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: { redirect: '/workbench' } }),
}));
vi.mock('@vben/locales', () => ({ $t: (key: string) => key }));
vi.mock(
  '../../dushan-admin-frontend/apps/web-ele/src/views/_core/authentication/social-oauth',
  async (original) => ({
    ...(await original<object>()),
    beginSocialOAuth: stubs.begin,
  }),
);
const cleanups: Array<() => void> = [];
beforeEach(() => {
  vi.clearAllMocks();
  vi.stubEnv('VITE_APP_SOCIAL_LOGIN_ENABLE', 'true');
});
afterEach(() => {
  for (const close of cleanups.splice(0)) close();
  vi.unstubAllEnvs();
});
function mount() {
  const props = reactive({
    disabled: false,
    selectTenant: true,
    tenantId: undefined as string | undefined,
  });
  const element = document.createElement('div');
  const app = createApp(() => h(SocialLoginOptions, props));
  app.mount(element);
  cleanups.push(() => app.unmount());
  return { props, element };
}

it('未选租户不请求渠道；只显示支持渠道，点击使用当前租户', async () => {
  const { props, element } = mount();
  expect(stubs.providers).not.toHaveBeenCalled();
  stubs.providers.mockResolvedValue([
    {
      type: 20,
      source: 'DINGTALK',
      name: '钉钉',
      mode: 'browser',
      codeParameter: 'code',
    },
    {
      type: 30,
      source: 'WECHAT_ENTERPRISE',
      name: '企业微信',
      mode: 'browser',
      codeParameter: 'code',
    },
  ]);
  props.tenantId = '2';
  await vi.waitFor(() =>
    expect(element.querySelectorAll('button')).toHaveLength(2),
  );
  expect(element.textContent).toContain('钉钉');
  expect(element.textContent).toContain('企业微信');
  element
    .querySelector<HTMLButtonElement>('button[aria-label="钉钉"]')!
    .click();
  await vi.waitFor(() =>
    expect(stubs.begin).toHaveBeenCalledWith({
      type: 20,
      codeParameter: 'code',
      tenantId: '2',
      returnPath: '/workbench',
    }),
  );
});

it('关闭开关不查询、不渲染入口或错误，租户变化也不请求', async () => {
  vi.stubEnv('VITE_APP_SOCIAL_LOGIN_ENABLE', 'false');
  const { props, element } = mount();
  props.tenantId = '1';
  await nextTick();
  props.tenantId = '2';
  await nextTick();
  expect(stubs.providers).not.toHaveBeenCalled();
  expect(element.textContent).toBe('');
});

it('切换租户后忽略旧列表的迟到响应；双关租户模式不携带历史选择', async () => {
  const pending = Promise.withResolvers<number[]>();
  stubs.providers.mockReturnValueOnce(pending.promise).mockResolvedValue([]);
  const { props, element } = mount();
  props.tenantId = '1';
  await nextTick();
  props.tenantId = '2';
  await nextTick();
  pending.resolve([20]);
  await nextTick();
  expect(element.querySelectorAll('button')).toHaveLength(0);
  props.selectTenant = false;
  props.tenantId = undefined;
  await nextTick();
  expect(stubs.providers).toHaveBeenLastCalledWith(undefined);
});
