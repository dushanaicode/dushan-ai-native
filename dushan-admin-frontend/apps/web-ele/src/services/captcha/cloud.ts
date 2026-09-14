import type { CaptchaAnswer, CaptchaChallenge } from './schema';

import { acquireCaptchaScript } from './script-loader';

// cspell:words Aliyun
export interface AliyunInstance {
  show: () => void;
  refresh: () => void;
  destroyCaptcha: () => void;
}
export interface TencentInstance {
  show: () => void;
  destroy: () => void;
}
interface TencentResult {
  ret: number;
  ticket?: string;
  randstr?: string;
  errorCode?: number;
}
interface CloudWindow extends Window {
  AliyunCaptchaConfig?: { region: string; prefix: string };
  initAliyunCaptcha?: (options: {
    SceneId: string;
    mode: 'popup';
    element: string;
    button: string;
    language: string;
    getInstance: (instance: AliyunInstance) => void;
    captchaVerifyCallback: (
      value: string,
    ) => Promise<{ captchaResult: boolean }>;
    onBizResultCallback: (result: boolean) => void;
  }) => void;
  TencentCaptcha?: new (
    appId: string,
    callback: (result: TencentResult) => void,
    options: { userLanguage: string; showFn: () => void },
  ) => TencentInstance;
}

export async function mountCloudCaptcha(options: {
  challenge: Extract<CaptchaChallenge, { provider: 'aliyun' | 'tencent' }>;
  element: HTMLElement;
  button: HTMLButtonElement;
  signal: AbortSignal;
  language: string;
  verify: (answer: CaptchaAnswer) => Promise<unknown>;
  cancel: () => void;
  onError: (error: unknown) => void;
}) {
  const global = window as CloudWindow;
  const { challenge, signal } = options;
  let instance: AliyunInstance | TencentInstance | undefined;
  let active = true;
  let warmup: ReturnType<typeof setTimeout> | undefined;
  const url =
    challenge.provider === 'aliyun'
      ? 'https://o.alicdn.com/captcha-frontend/aliyunCaptcha/AliyunCaptcha.js'
      : 'https://turing.captcha.qcloud.com/TJCaptcha.js';
  const identity =
    challenge.provider === 'aliyun'
      ? `${challenge.data.region}:${challenge.data.prefix}`
      : 'tencent';
  const lease = acquireCaptchaScript(
    url,
    signal,
    identity,
    challenge.provider === 'aliyun'
      ? () => {
          global.AliyunCaptchaConfig = {
            region: challenge.data.region,
            prefix: challenge.data.prefix,
          };
        }
      : undefined,
  );
  const dispose = () => {
    if (!active) return;
    active = false;
    clearTimeout(warmup);
    signal.removeEventListener('abort', dispose);
    if (instance) {
      if ('destroyCaptcha' in instance) instance.destroyCaptcha();
      else instance.destroy();
    }
    lease.release();
  };
  signal.addEventListener('abort', dispose, { once: true });
  options.button.disabled = true;
  try {
    await lease.ready;
    signal.throwIfAborted();
    if (challenge.provider === 'aliyun') {
      const initialize = global.initAliyunCaptcha;
      if (!initialize) throw new Error('验证码 SDK 未提供 initAliyunCaptcha');
      await new Promise<void>((resolve, reject) => {
        const cleanup = () => {
          clearTimeout(timeout);
          signal.removeEventListener('abort', abort);
        };
        const timeout = setTimeout(() => {
          cleanup();
          reject(new Error('验证码初始化超时'));
        }, 10_000);
        const abort = () => {
          cleanup();
          reject(new DOMException('验证码初始化已取消', 'AbortError'));
        };
        signal.addEventListener('abort', abort, { once: true });
        try {
          initialize({
            SceneId: challenge.data.scene_id,
            mode: 'popup',
            element: `#${options.element.id}`,
            button: `#${options.button.id}`,
            language: challenge.data.language,
            getInstance(value) {
              cleanup();
              if (!active) {
                value.destroyCaptcha();
                return;
              }
              instance = value;
              resolve();
            },
            async captchaVerifyCallback(parameter) {
              if (!active) return { captchaResult: false };
              try {
                await options.verify({ captcha_verify_param: parameter });
                return { captchaResult: true };
              } catch (error) {
                options.onError(error);
                return { captchaResult: false };
              }
            },
            // 此处只签发验证凭证，业务执行由调用方处理。
            onBizResultCallback: () => undefined,
          });
        } catch (error) {
          cleanup();
          reject(error);
        }
      });
      warmup = setTimeout(() => {
        if (active) options.button.disabled = false;
      }, 2000);
    } else {
      const Create = global.TencentCaptcha;
      if (!Create) throw new Error('验证码 SDK 未提供 TencentCaptcha');
      instance = new Create(
        challenge.data.app_id,
        (result) => {
          if (!active) return;
          clearTimeout(warmup);
          if (result.ret === 2) {
            options.cancel();
            return;
          }
          if (
            result.ret !== 0 ||
            (result.errorCode !== undefined && result.errorCode !== 0) ||
            !result.ticket ||
            !result.randstr
          ) {
            options.onError(new Error('验证码服务未返回有效凭据'));
            return;
          }
          options.button.disabled = true;
          void options
            .verify({ ticket: result.ticket, randstr: result.randstr })
            .catch(options.onError)
            .finally(() => {
              if (active) options.button.disabled = false;
            });
        },
        { userLanguage: options.language, showFn: () => clearTimeout(warmup) },
      );
      options.button.disabled = false;
      options.button.addEventListener(
        'click',
        () => {
          if (active && instance && 'destroy' in instance) {
            clearTimeout(warmup);
            warmup = setTimeout(() => {
              if (active) options.onError(new Error('验证码显示超时'));
            }, 10_000);
            instance.show();
          }
        },
        { signal },
      );
    }
    return dispose;
  } catch (error) {
    dispose();
    throw error;
  }
}
