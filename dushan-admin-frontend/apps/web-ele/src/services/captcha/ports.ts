import type { CaptchaPorts } from './controller';

import {
  checkCaptcha,
  getCaptchaChallenge,
  getCaptchaConfig,
} from '#/api/core/captcha';

/**
 * 验证码服务端口，把 `services/captcha` 控制器接到 `/system/captcha/*` 端点。
 * challenge/verification 线上保持 snake_case，由 schema 层统一校验解析。
 */
export function createCaptchaPorts(): CaptchaPorts {
  return {
    configuration: (signal) => getCaptchaConfig(signal),
    challenge: (purpose, signal) => getCaptchaChallenge(purpose, signal),
    check: (token, purpose, answer, signal) =>
      checkCaptcha(token, purpose, answer, signal),
  };
}
