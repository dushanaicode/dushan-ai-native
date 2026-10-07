/* eslint-disable vue/one-component-per-file -- 分别验证独立应用的错误边界。 */
import { createApp, h } from 'vue';

import { afterEach, assert, beforeEach, expect, it, vi } from 'vitest';

import { FormSubmission } from '../../dushan-admin-frontend/apps/web-ele/src/adapter/form-submission';
import { BusinessError } from '../../dushan-admin-frontend/apps/web-ele/src/api/business-error';
import {
  installDemoErrorBoundary,
  notifyError,
} from '../../dushan-admin-frontend/apps/web-ele/src/api/error-feedback';
import {
  anonymousClient,
  requestClient,
} from '../../dushan-admin-frontend/apps/web-ele/src/api/request';

const stubs = vi.hoisted(() => ({ error: vi.fn(), warning: vi.fn() }));
vi.mock('@vben/hooks', () => ({
  useAppConfig: () => ({ apiURL: 'http://testserver/admin-api' }),
}));
vi.mock('@vben/locales', () => ({
  $t: (key: string) =>
    key === 'readonlyDemo.denied' ? '只读演示模式：不能执行修改操作' : key,
}));
vi.mock('element-plus', () => ({ ElMessage: stubs }));
vi.mock('#/services/session/runtime', () => ({
  getSession: () => ({
    capture: () => ({ generation: 'demo', token: 'demo-token' }),
    assertCurrent: (scope: unknown) => scope,
  }),
}));
const cleanups: Array<() => void> = [];
beforeEach(() => vi.clearAllMocks());
afterEach(() => {
  for (const cleanup of cleanups.splice(0)) cleanup();
  vi.restoreAllMocks();
});
function rejectedWrite(
  code = 901,
  errorMessageMode: 'form' | 'message' = 'message',
  client = anonymousClient,
) {
  return client.post(
    '/write',
    {},
    {
      errorMessageMode,
      adapter: async (config) => ({
        config,
        data: { code, message: '后端原始错误', data: null, error: null },
        status: 200,
        statusText: 'OK',
        headers: {},
      }),
    },
  );
}
function rejectionEvent(reason: unknown) {
  return Object.assign(new Event('unhandledrejection', { cancelable: true }), {
    reason,
    promise: Promise.resolve(),
  });
}
it.each(['message', 'form'] as const)(
  '901 %s 请求只提示警告并拒绝，后续成功操作不执行',
  async (mode) => {
    const success = vi.fn();
    const finalized = vi.fn();
    const operation = (async () => {
      try {
        await rejectedWrite(901, mode);
        success();
      } finally {
        finalized();
      }
    })();
    await expect(operation).rejects.toMatchObject({ code: 901 });
    expect(success).not.toHaveBeenCalled();
    expect(finalized).toHaveBeenCalledOnce();
    expect(stubs.warning).toHaveBeenCalledExactlyOnceWith(
      '只读演示模式：不能执行修改操作',
    );
    expect(stubs.error).not.toHaveBeenCalled();
  },
);
it('表单消费 901 时维持失败状态且不追加原始错误提示', async () => {
  const notify = vi.fn();
  const submission = new FormSubmission(
    {
      isMounted: true,
      getRawValues: async () => ({}),
      getFieldComponentRef: () => undefined,
      setFieldError: async () => {},
      scrollToFirstError: () => {},
    },
    notify,
  );
  expect(
    await submission.submit((config) =>
      rejectedWrite(901, config.errorMessageMode),
    ),
  ).toEqual({ status: 'error' });
  expect(stubs.warning).toHaveBeenCalledOnce();
  expect(notify).not.toHaveBeenCalled();
});
it('其它业务错误保留原始错误等级和拒绝', async () => {
  await expect(rejectedWrite(422)).rejects.toMatchObject({ code: 422 });
  expect(stubs.error).toHaveBeenCalledExactlyOnceWith('后端原始错误');
  expect(stubs.warning).not.toHaveBeenCalled();
});
it('携带登录会话的业务请求只提示一次警告并保持拒绝', async () => {
  await expect(
    rejectedWrite(901, 'message', requestClient),
  ).rejects.toMatchObject({
    code: 901,
    config: { headers: { Authorization: 'Bearer demo-token' } },
  });
  expect(stubs.warning).toHaveBeenCalledExactlyOnceWith(
    '只读演示模式：不能执行修改操作',
  );
  expect(stubs.error).not.toHaveBeenCalled();
});
it('没有既有 Vue 错误处理器时，普通异常仍抛出原始错误', () => {
  const app = createApp({ render: () => null });
  cleanups.push(installDemoErrorBoundary(app));
  const original = new Error('程序错误');
  const handler = app.config.errorHandler;
  assert(handler);
  expect(() => handler(original, null, 'test')).toThrow(original);
});
it('vue async 点击边界消费 901，清除 loading 且不记录系统错误', async () => {
  const success = vi.fn();
  const finalized = vi.fn();
  const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
  const app = createApp({
    render: () =>
      h(
        'button',
        {
          onClick: async () => {
            try {
              await rejectedWrite();
              success();
            } finally {
              finalized();
            }
          },
        },
        '保存',
      ),
  });
  cleanups.push(installDemoErrorBoundary(app));
  const host = document.createElement('div');
  app.mount(host);
  cleanups.push(() => app.unmount());
  const button = host.querySelector('button');
  assert(button);
  button.click();
  await vi.waitFor(() => expect(finalized).toHaveBeenCalledOnce());
  expect(success).not.toHaveBeenCalled();
  expect(consoleError).not.toHaveBeenCalled();
  expect(stubs.warning).toHaveBeenCalledOnce();
});
it('最终 Promise 边界仅消费 901，重复不提示并在卸载时恢复', () => {
  const app = createApp({ render: () => null });
  const previous = vi.fn();
  app.config.errorHandler = previous;
  const release = installDemoErrorBoundary(app);
  cleanups.push(release);
  const handler = app.config.errorHandler;
  assert(handler);
  const denied = new BusinessError(
    { code: 901, message: '原始错误', data: null, error: null },
    {},
  );
  notifyError(denied);
  const event = rejectionEvent(denied);
  window.dispatchEvent(event);
  expect(event.defaultPrevented).toBe(true);
  expect(stubs.warning).toHaveBeenCalledOnce();
  for (const reason of [
    new Error('故障'),
    new BusinessError(
      { code: 422, message: '其它错误', data: null, error: null },
      {},
    ),
  ]) {
    const other = rejectionEvent(reason);
    window.dispatchEvent(other);
    expect(other.defaultPrevented).toBe(false);
    handler(reason, null, 'test');
    expect(previous).toHaveBeenLastCalledWith(reason, null, 'test');
  }
  release();
  expect(app.config.errorHandler).toBe(previous);
  const afterRelease = rejectionEvent(denied);
  window.dispatchEvent(afterRelease);
  expect(afterRelease.defaultPrevented).toBe(false);
});
