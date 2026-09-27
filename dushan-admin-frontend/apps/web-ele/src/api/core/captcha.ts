import { preferences } from '@vben/preferences';

import { authenticationClient } from '#/api/request';

/**
 * 验证码端点。challenge/verification 由后端 framework 普通 BaseModel 序列化，
 * 线上字段保持 snake_case（`expires_in`/`captcha_verify_param`），不做 camel 化。
 */
export namespace CaptchaApi {
  /** GET /system/captcha/config 响应 */
  export interface CaptchaConfig {
    enabled: boolean;
    provider: 'aliyun' | 'block_puzzle' | 'click_word' | 'tencent';
    purposes: string[];
  }

  /** POST /system/captcha/get 响应（data 内容按 provider 由 services/captcha 校验） */
  export interface CaptchaChallenge {
    data: Record<string, unknown>;
    expires_in: number;
    provider: string;
    purpose: string;
    token: string;
  }

  /** POST /system/captcha/check 的 answer 字段（CaptchaAnswer，snake_case） */
  export interface CaptchaAnswer {
    captcha_verify_param?: string;
    points?: { x: number; y: number }[];
    randstr?: string;
    ticket?: string;
  }

  /** POST /system/captcha/check 响应 */
  export interface CaptchaVerification {
    expires_in: number;
    purpose: string;
    verification: string;
  }
}

/** 获取验证码配置 */
export async function getCaptchaConfig(signal?: AbortSignal) {
  return authenticationClient.get<CaptchaApi.CaptchaConfig>(
    '/system/captcha/config',
    captchaRequest(signal),
  );
}

/** 获取验证码挑战 */
export async function getCaptchaChallenge(
  purpose: string,
  signal?: AbortSignal,
) {
  return authenticationClient.post<CaptchaApi.CaptchaChallenge>(
    '/system/captcha/get',
    { purpose },
    captchaRequest(signal),
  );
}

/** 校验验证码答案，返回短期凭证 */
export async function checkCaptcha(
  challengeId: string,
  purpose: string,
  answer: CaptchaApi.CaptchaAnswer,
  signal?: AbortSignal,
) {
  return authenticationClient.post<CaptchaApi.CaptchaVerification>(
    '/system/captcha/check',
    { answer, challengeId, purpose },
    captchaRequest(signal),
  );
}

/** 公开验证码由弹窗呈现错误，不触发全局消息或已有会话的刷新。 */
function captchaRequest(signal?: AbortSignal) {
  return { signal, headers: { 'Accept-Language': preferences.app.locale } };
}
