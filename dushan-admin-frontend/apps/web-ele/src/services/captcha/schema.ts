import { z } from '@vben/common-ui';

// cspell:words Aliyun
const token = z.string().regex(/^[A-Za-z0-9_-]{43}$/);
const provider = z.enum(['block_puzzle', 'click_word', 'aliyun', 'tencent']);
const base = z.object({
  token,
  purpose: z.string().min(1),
  expires_in: z.number().int().positive(),
});
const image = z.object({
  width: z.literal(320),
  height: z.literal(160),
  format: z.literal('jpeg'),
  piece_format: z.literal('png'),
  coordinates: z.literal('original_pixels'),
  image: z.string().min(1),
});
export const captchaConfigSchema = z
  .object({
    enabled: z.boolean(),
    provider,
    purposes: z.array(z.string().min(1)),
  })
  .strict();
export const captchaChallengeSchema = z.discriminatedUnion('provider', [
  base
    .extend({
      provider: z.literal('block_puzzle'),
      data: image
        .extend({
          piece: z.string().min(1),
          piece_width: z.number().positive().lt(320),
          axis: z.literal('x'),
          origin_y: z.literal(0),
        })
        .strict(),
    })
    .strict(),
  base
    .extend({
      provider: z.literal('click_word'),
      data: image
        .extend({ words: z.array(z.string().min(1)).length(3) })
        .strict(),
    })
    .strict(),
  base
    .extend({
      provider: z.literal('aliyun'),
      data: z
        .object({
          scene_id: z.string().min(1),
          prefix: z.string().min(1),
          region: z.string().min(1),
          language: z.string().min(1),
        })
        .strict(),
    })
    .strict(),
  base
    .extend({
      provider: z.literal('tencent'),
      data: z.object({ app_id: z.string().min(1) }).strict(),
    })
    .strict(),
]);
export const captchaVerificationSchema = z
  .object({
    verification: token,
    purpose: z.string().min(1),
    expires_in: z.number().int().positive(),
  })
  .strict();
export type CaptchaChallenge = z.infer<typeof captchaChallengeSchema>;
export type CaptchaVerification = z.infer<typeof captchaVerificationSchema>;
export type CaptchaConfig = z.infer<typeof captchaConfigSchema>;
export interface CaptchaPoint {
  x: number;
  y: number;
}
export type CaptchaAnswer =
  | { captcha_verify_param: string }
  | { points: CaptchaPoint[] }
  | { ticket: string; randstr: string };

const point = z
  .object({ x: z.number().min(0).lt(320), y: z.number().min(0).lt(160) })
  .strict();
export function parseCaptchaAnswer(
  challenge: CaptchaChallenge,
  value: unknown,
): CaptchaAnswer {
  switch (challenge.provider) {
    case 'block_puzzle': {
      return z
        .object({
          points: z.array(point.extend({ y: z.literal(0) })).length(1),
        })
        .strict()
        .parse(value);
    }
    case 'click_word': {
      return z
        .object({ points: z.array(point).length(challenge.data.words.length) })
        .strict()
        .parse(value);
    }
    case 'aliyun': {
      return z
        .object({ captcha_verify_param: z.string().min(1).max(16_384) })
        .strict()
        .parse(value);
    }
    case 'tencent': {
      return z
        .object({
          ticket: z.string().min(1).max(4096),
          randstr: z.string().min(1).max(4096),
        })
        .strict()
        .parse(value);
    }
  }
}

export function toOriginalPoint(
  x: number,
  y: number,
  width: number,
  height: number,
): CaptchaPoint {
  if (
    ![x, y, width, height].every((value) => Number.isFinite(value)) ||
    width <= 0 ||
    height <= 0 ||
    x < 0 ||
    y < 0 ||
    x > width ||
    y > height
  )
    throw new TypeError('验证码显示坐标无效');
  return {
    x: Math.min(319, (x / width) * 320),
    y: Math.min(159, (y / height) * 160),
  };
}
