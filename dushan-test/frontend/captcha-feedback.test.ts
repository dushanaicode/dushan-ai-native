import { createApp, nextTick } from 'vue';

import { initStores } from '@vben/stores';

import { afterEach, beforeEach, expect, it, vi } from 'vitest';

import {
  anonymousClient,
  authenticationClient,
  requestClient,
} from '../../dushan-admin-frontend/apps/web-ele/src/api/request';
import Login from '../../dushan-admin-frontend/apps/web-ele/src/views/_core/authentication/login.vue';

const state = vi.hoisted(() => ({
  login: vi.fn(),
  message: vi.fn(),
  session: vi.fn(),
  mode: 'wrong' as 'network' | 'refreshFailed' | 'wrong',
  challenges: 0,
  checks: 0,
  requests: [] as any[],
}));
vi.mock('@vben/hooks', () => ({
  useAppConfig: () => ({ apiURL: 'http://testserver/admin-api' }),
}));
vi.mock('@vben/locales', () => ({ $t: (key: string) => key }));
vi.mock('vue-router', () => ({ useRoute: () => ({ query: {} }) }));
vi.mock('#/api/core/auth', () => ({
  getLoginTenantsApi: async () => ({ enabled: false, tenants: [] }),
  isRegistrationEnabled: async () => false,
}));
vi.mock('#/store', () => ({
  useAuthStore: () => ({ authLogin: state.login, loginLoading: false }),
}));
vi.mock('#/services/session/runtime', () => ({ getSession: state.session }));
vi.mock('element-plus', async () => {
  const { defineComponent, h } = await import('vue');
  return {
    ElMessage: { error: state.message },
    ElDialog: defineComponent({
      props: { modelValue: Boolean, title: String },
      setup(props, { slots }) {
        return () =>
          props.modelValue
            ? h('div', { role: 'dialog' }, slots.default?.())
            : null;
      },
    }),
    ElAlert: defineComponent({
      props: { title: String, type: String, closable: Boolean },
      setup(props) {
        return () => h('div', { role: 'alert' }, props.title);
      },
    }),
    ElButton: defineComponent({
      setup(_, { slots }) {
        return () => h('button', slots.default?.());
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
        setup(_, { emit, expose }) {
          expose({ getFormApi: () => ({ setFieldValue: vi.fn() }) });
          return () =>
            h(
              'button',
              {
                'data-login': '',
                onClick: () =>
                  emit('submit', {
                    username: 'admin',
                    password: 'test-password',
                  }),
              },
              'Login',
            );
        },
      }),
    };
  },
);
vi.mock(
  '../../dushan-admin-frontend/apps/web-ele/src/components/captcha/local-captcha.vue',
  async () => {
    const { defineComponent, h } = await import('vue');
    return {
      default: defineComponent({
        emits: ['answer'],
        setup(_, { emit }) {
          return () =>
            h(
              'button',
              {
                'data-answer': '',
                onClick: () =>
                  emit('answer', {
                    points: [
                      { x: 1, y: 1 },
                      { x: 2, y: 2 },
                      { x: 3, y: 3 },
                    ],
                  }),
              },
              'Answer',
            );
        },
      }),
    };
  },
);

const cleanups: Array<() => void> = [];
beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  vi.stubEnv('VITE_APP_SOCIAL_LOGIN_ENABLE', 'false');
  state.mode = 'wrong';
  state.challenges = 0;
  state.checks = 0;
  state.requests = [];
  state.session.mockReturnValue({
    capture: () => ({ generation: 'old', token: 'old' }),
    assertCurrent: (value: unknown) => value,
  });
  const adapter = async (config: any) => {
    state.requests.push(config);
    let data: unknown;
    if (config.url.endsWith('/config')) {
      if (state.mode === 'network') throw new Error('network failed');
      data = { enabled: true, provider: 'click_word', purposes: ['login'] };
    } else if (config.url.endsWith('/get')) {
      state.challenges++;
      if (state.mode === 'refreshFailed' && state.challenges > 1) {
        return response(config, {
          code: 1002007,
          message: '验证码服务暂不可用',
          data: null,
          error: null,
        });
      }
      data = {
        token: String(state.challenges).repeat(43),
        purpose: 'login',
        provider: 'click_word',
        expires_in: 60,
        data: {
          width: 320,
          height: 160,
          format: 'jpeg',
          piece_format: 'png',
          coordinates: 'original_pixels',
          image: 'a',
          words: ['甲', '乙', '丙'],
        },
      };
    } else if (config.url.endsWith('/check')) {
      state.checks++;
      if (state.checks === 1)
        return response(config, {
          code: 1002002,
          message: '验证码答案错误',
          data: null,
          error: null,
        });
      data = { verification: 'v'.repeat(43), purpose: 'login', expires_in: 30 };
    } else {
      throw new Error(`Unexpected request: ${config.url}`);
    }
    return response(config, { code: 0, message: '', data, error: null });
  };
  // 真实请求拦截器仍运行，只替换 HTTP 传输，旧代码会触发全局错误提示。
  for (const client of [anonymousClient, authenticationClient, requestClient]) {
    const get = client.get.bind(client);
    const post = client.post.bind(client);
    vi.spyOn(client, 'get').mockImplementation((url, config) =>
      get(url, { ...config, adapter }),
    );
    vi.spyOn(client, 'post').mockImplementation((url, data, config) =>
      post(url, data, { ...config, adapter }),
    );
  }
});
afterEach(() => {
  for (const cleanup of cleanups.splice(0)) cleanup();
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
});

function response(config: any, data: unknown) {
  return { config, data, status: 200, statusText: 'OK', headers: {} };
}

async function openCaptcha() {
  const element = document.createElement('div');
  const app = createApp(Login);
  await initStores(app, { namespace: 'captcha-feedback-test' });
  app.mount(element);
  cleanups.push(() => app.unmount());
  await nextTick();
  element.querySelector<HTMLButtonElement>('[data-login]')!.click();
  return element;
}

it('答案错误只保留一条具体横幅；自动换题后可重试，手动刷新清除旧错误', async () => {
  const element = await openCaptcha();
  await vi.waitFor(() =>
    expect(element.querySelector('[data-answer]')).not.toBeNull(),
  );
  element.querySelector<HTMLButtonElement>('[data-answer]')!.click();
  await vi.waitFor(() => {
    expect(element.querySelectorAll('[role="alert"]')).toHaveLength(1);
    expect(element.querySelector('[role="alert"]')!.textContent).toBe(
      '验证码答案错误',
    );
    expect(state.challenges).toBe(2);
  });
  expect(state.message).not.toHaveBeenCalled();
  expect(state.session).not.toHaveBeenCalled();
  expect(state.login).not.toHaveBeenCalled();
  expect(element.textContent).not.toContain('验证码加载失败');
  [...element.querySelectorAll<HTMLButtonElement>('button')]
    .find((button) => button.textContent === 'utils.captcha.refresh')!
    .click();
  await vi.waitFor(() => expect(state.challenges).toBe(3));
  expect(element.querySelector('[role="alert"]')).toBeNull();
  element.querySelector<HTMLButtonElement>('[data-answer]')!.click();
  await vi.waitFor(() => expect(state.login).toHaveBeenCalledOnce());
  expect(state.login.mock.calls[0][0].verification).toBe('v'.repeat(43));
  expect(element.querySelector('[role="dialog"]')).toBeNull();
  expect(state.message).not.toHaveBeenCalled();
  expect(state.requests[0].headers.get('Accept-Language')).toBeTruthy();
});

it('初始加载网络失败也只在弹窗内提示，不弹全局消息', async () => {
  state.mode = 'network';
  const element = await openCaptcha();
  await vi.waitFor(() =>
    expect(element.querySelectorAll('[role="alert"]')).toHaveLength(1),
  );
  expect(element.querySelector('[role="alert"]')!.textContent).toBe(
    'utils.captcha.failed',
  );
  expect(state.message).not.toHaveBeenCalled();
  expect(state.login).not.toHaveBeenCalled();
});

it('答错后换题失败，单一横幅呈现当前换题故障，不叠加旧错误', async () => {
  state.mode = 'refreshFailed';
  const element = await openCaptcha();
  await vi.waitFor(() =>
    expect(element.querySelector('[data-answer]')).not.toBeNull(),
  );
  element.querySelector<HTMLButtonElement>('[data-answer]')!.click();
  await vi.waitFor(() => {
    expect(element.querySelectorAll('[role="alert"]')).toHaveLength(1);
    expect(element.querySelector('[role="alert"]')!.textContent).toBe(
      '验证码服务暂不可用',
    );
  });
  expect(state.message).not.toHaveBeenCalled();
  expect(state.login).not.toHaveBeenCalled();
});
