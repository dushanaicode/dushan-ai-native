import { afterEach, expect, it, vi } from 'vitest';

import { mountCloudCaptcha } from '../../dushan-admin-frontend/apps/web-ele/src/services/captcha/cloud';
import { captchaChallengeSchema } from '../../dushan-admin-frontend/apps/web-ele/src/services/captcha/schema';

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});
function setup(provider: 'aliyun' | 'tencent') {
  vi.useFakeTimers();
  const appended: HTMLScriptElement[] = [];
  vi.spyOn(document.head, 'append').mockImplementation((...nodes) => {
    appended.push(nodes[0] as HTMLScriptElement);
  });
  const controller = new AbortController();
  const button = document.createElement('button');
  const element = document.createElement('div');
  button.id = 'captcha-button';
  element.id = 'captcha-element';
  const value = captchaChallengeSchema.parse({
    token: 'a'.repeat(43),
    purpose: 'login',
    expires_in: 60,
    provider,
    data:
      provider === 'aliyun'
        ? { scene_id: 'scene', region: 'cn', prefix: 'prefix', language: 'cn' }
        : { app_id: '12345678901234567890' },
  });
  const verify = vi.fn(async () => undefined);
  const onError = vi.fn();
  const cancel = vi.fn();
  const start = () =>
    mountCloudCaptcha({
      challenge: value as Extract<
        typeof value,
        { provider: 'aliyun' | 'tencent' }
      >,
      element,
      button,
      signal: controller.signal,
      language: 'zh-cn',
      verify,
      cancel,
      onError,
    });
  return { start, appended, controller, button, verify, onError, cancel };
}
it('阿里云透传不透明参数，由服务器结果决定回调，卸载销毁 SDK', async () => {
  const context = setup('aliyun');
  const destroyCaptcha = vi.fn();
  let callback!: (value: string) => Promise<{ captchaResult: boolean }>;
  vi.stubGlobal(
    'initAliyunCaptcha',
    (options: {
      getInstance: (instance: unknown) => void;
      captchaVerifyCallback: typeof callback;
    }) => {
      callback = options.captchaVerifyCallback;
      options.getInstance({ show: vi.fn(), refresh: vi.fn(), destroyCaptcha });
    },
  );
  const started = context.start();
  context.appended[0]!.dispatchEvent(new Event('load'));
  await started;
  expect(context.button.disabled).toBe(true);
  await vi.advanceTimersByTimeAsync(2000);
  expect(context.button.disabled).toBe(false);
  await expect(callback('opaque-parameter')).resolves.toEqual({
    captchaResult: true,
  });
  expect(context.verify).toHaveBeenCalledWith({
    captcha_verify_param: 'opaque-parameter',
  });
  context.verify.mockRejectedValueOnce(new Error('rejected'));
  await expect(callback('bad')).resolves.toEqual({ captchaResult: false });
  expect(context.onError).toHaveBeenCalledOnce();
  context.controller.abort();
  expect(destroyCaptcha).toHaveBeenCalledOnce();
  await expect(callback('late')).resolves.toEqual({ captchaResult: false });
  expect(context.verify).toHaveBeenCalledTimes(2);
  expect(vi.getTimerCount()).toBe(0);
});
it('腾讯保留字符串应用 ID，取消及错误不提交，成功仍调用服务器，卸载后事件失效', async () => {
  const context = setup('tencent');
  const destroy = vi.fn();
  const show = vi.fn();
  let callback!: (value: {
    ret: number;
    ticket?: string;
    randstr?: string;
    errorCode?: number;
  }) => void;
  let appId = '';
  vi.stubGlobal(
    'TencentCaptcha',
    class {
      destroy = destroy;
      show = show;
      constructor(id: string, cb: typeof callback) {
        appId = id;
        callback = cb;
      }
    },
  );
  const started = context.start();
  context.appended[0]!.dispatchEvent(new Event('load'));
  await started;
  expect(appId).toBe('12345678901234567890');
  context.button.click();
  expect(show).toHaveBeenCalledOnce();
  callback({ ret: 2 });
  expect(context.cancel).toHaveBeenCalledOnce();
  callback({ ret: 0, errorCode: 1001, ticket: 'invalid', randstr: 'x' });
  expect(context.verify).not.toHaveBeenCalled();
  callback({ ret: 0, ticket: 'ticket', randstr: 'random' });
  await vi.advanceTimersByTimeAsync(0);
  expect(context.verify).toHaveBeenCalledWith({
    ticket: 'ticket',
    randstr: 'random',
  });
  context.controller.abort();
  context.button.click();
  callback({ ret: 0, ticket: 'late', randstr: 'random' });
  expect(destroy).toHaveBeenCalledOnce();
  expect(show).toHaveBeenCalledOnce();
  expect(context.verify).toHaveBeenCalledOnce();
  expect(vi.getTimerCount()).toBe(0);
});
