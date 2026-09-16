import { afterEach, describe, expect, it, vi } from 'vitest';

import { CaptchaController } from '../../dushan-admin-frontend/apps/web-ele/src/services/captcha/controller';
import {
  captchaChallengeSchema,
  parseCaptchaAnswer,
  toOriginalPoint,
} from '../../dushan-admin-frontend/apps/web-ele/src/services/captcha/schema';
import { acquireCaptchaScript } from '../../dushan-admin-frontend/apps/web-ele/src/services/captcha/script-loader';

const challenge = {
  token: 'a'.repeat(43),
  provider: 'click_word',
  purpose: 'login',
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
const answer = {
  points: [
    { x: 0, y: 0 },
    { x: 100, y: 20 },
    { x: 319, y: 159 },
  ],
};
const verification = {
  verification: 'v'.repeat(43),
  purpose: 'login',
  expires_in: 30,
};
const disposers: Array<() => void> = [];
function setup() {
  const ports = {
    configuration: vi.fn(async () => ({
      enabled: true,
      provider: 'click_word',
      purposes: ['login'],
    })),
    challenge: vi.fn(async () => challenge),
    check: vi.fn(async () => verification),
  };
  const onError = vi.fn();
  const controller = new CaptchaController(ports, onError);
  disposers.push(() => controller.dispose());
  return { controller, ports, onError };
}
afterEach(() => {
  for (const dispose of disposers.splice(0)) dispose();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('服务端验证码流程', () => {
  it('原图换算保留原点、缩放和边界，拒绝无效尺寸', () => {
    expect(toOriginalPoint(0, 0, 160, 80)).toEqual({ x: 0, y: 0 });
    expect(toOriginalPoint(80, 40, 160, 80)).toEqual({ x: 160, y: 80 });
    expect(toOriginalPoint(160, 80, 160, 80)).toEqual({ x: 319, y: 159 });
    expect(() => toOriginalPoint(0, 0, 0, 80)).toThrow();
  });
  it('四种 provider 只接受各自答案，点选要求三个且不允许时间或加密字段', () => {
    const click = captchaChallengeSchema.parse(challenge);
    expect(parseCaptchaAnswer(click, answer)).toEqual(answer);
    expect(() =>
      parseCaptchaAnswer(click, { points: answer.points.slice(0, 2) }),
    ).toThrow();
    expect(() =>
      parseCaptchaAnswer(click, {
        points: answer.points.map((p) => ({ ...p, t: 1 })),
      }),
    ).toThrow();
    const { words: _words, ...image } = challenge.data;
    const puzzle = captchaChallengeSchema.parse({
      ...challenge,
      provider: 'block_puzzle',
      data: { ...image, piece: 'b', piece_width: 50, axis: 'x', origin_y: 0 },
    });
    expect(parseCaptchaAnswer(puzzle, { points: [{ x: 123, y: 0 }] })).toEqual({
      points: [{ x: 123, y: 0 }],
    });
    const aliyun = captchaChallengeSchema.parse({
      ...challenge,
      provider: 'aliyun',
      data: {
        scene_id: 'scene',
        prefix: 'prefix',
        region: 'cn',
        language: 'cn',
      },
    });
    expect(
      parseCaptchaAnswer(aliyun, { captcha_verify_param: 'opaque' }),
    ).toEqual({ captcha_verify_param: 'opaque' });
    const tencent = captchaChallengeSchema.parse({
      ...challenge,
      provider: 'tencent',
      data: { app_id: '12345678901234567890' },
    });
    expect(
      parseCaptchaAnswer(tencent, { ticket: 'ticket', randstr: 'random' }),
    ).toEqual({ ticket: 'ticket', randstr: 'random' });
    expect(() => parseCaptchaAnswer(tencent, answer)).toThrow();
  });
  it('并发提交只验证一次，凭证来自服务端', async () => {
    const { controller, ports } = setup();
    const flow = controller.acquire('login');
    await vi.waitFor(() => expect(controller.status).toBe('ready'));
    const first = controller.submit(answer);
    expect(controller.submit(answer)).toBe(first);
    await expect(first).resolves.toEqual(verification);
    await expect(flow).resolves.toEqual(verification);
    expect(ports.check).toHaveBeenCalledTimes(1);
  });
  it('失败刷新挑战，允许同一流程重试', async () => {
    const { controller, ports } = setup();
    ports.check.mockRejectedValueOnce(new Error('答案错误'));
    const flow = controller.acquire('login');
    await vi.waitFor(() => expect(controller.status).toBe('ready'));
    await expect(controller.submit(answer)).rejects.toThrow('答案错误');
    expect(ports.challenge).toHaveBeenCalledTimes(2);
    await controller.submit(answer);
    await expect(flow).resolves.toEqual(verification);
  });
  it('过期重新取题，取消后晚到的校验不能签发凭证', async () => {
    vi.useFakeTimers();
    const { controller, ports } = setup();
    const flow = controller.acquire('login');
    const canceled = expect(flow).rejects.toMatchObject({ name: 'AbortError' });
    await vi.advanceTimersByTimeAsync(1);
    await vi.advanceTimersByTimeAsync(60_000);
    expect(ports.challenge).toHaveBeenCalledTimes(2);
    const pending = Promise.withResolvers<typeof verification>();
    ports.check.mockReturnValueOnce(pending.promise);
    const checking = controller.submit(answer);
    const stale = expect(checking).rejects.toMatchObject({
      name: 'AbortError',
    });
    controller.cancel();
    pending.resolve(verification);
    await canceled;
    await stale;
    expect(controller.status).toBe('idle');
  });
  it('配置关闭无需挑战；用途不匹配留在错误态', async () => {
    const { controller, ports, onError } = setup();
    ports.configuration.mockResolvedValueOnce({
      enabled: false,
      provider: 'click_word',
      purposes: [],
    });
    await expect(controller.acquire('login')).resolves.toBeNull();
    expect(ports.challenge).not.toHaveBeenCalled();
    const flow = controller.acquire('payment');
    const canceled = expect(flow).rejects.toMatchObject({ name: 'AbortError' });
    await vi.waitFor(() => expect(controller.status).toBe('error'));
    expect(onError).toHaveBeenCalledOnce();
    controller.cancel();
    await canceled;
  });
});

describe('验证码脚本租约', () => {
  it('并发加载复用，单个取消不影响另一等待者，全部卸载移除节点，再挂载不下载', async () => {
    const appended: HTMLScriptElement[] = [];
    vi.spyOn(document.head, 'append').mockImplementation((...nodes) => {
      appended.push(nodes[0] as HTMLScriptElement);
    });
    const a = new AbortController();
    const b = new AbortController();
    const url = 'https://captcha.example/reuse.js';
    const first = acquireCaptchaScript(url, a.signal, 'x');
    const second = acquireCaptchaScript(url, b.signal, 'x');
    const canceled = expect(first.ready).rejects.toMatchObject({
      name: 'AbortError',
    });
    a.abort();
    appended[0]!.dispatchEvent(new Event('load'));
    await canceled;
    await second.ready;
    expect(appended).toHaveLength(1);
    const remove = vi.spyOn(appended[0]!, 'remove');
    second.release();
    expect(remove).toHaveBeenCalled();
    const again = acquireCaptchaScript(url, b.signal, 'x');
    await again.ready;
    again.release();
    expect(appended).toHaveLength(1);
    expect(() => acquireCaptchaScript(url, b.signal, 'other')).toThrow('配置');
  });
  it('加载超时清理并可重试，卸载未加载脚本会取消', async () => {
    vi.useFakeTimers();
    const appended: HTMLScriptElement[] = [];
    vi.spyOn(document.head, 'append').mockImplementation((...nodes) => {
      appended.push(nodes[0] as HTMLScriptElement);
    });
    const controller = new AbortController();
    const url = 'https://captcha.example/timeout.js';
    const first = acquireCaptchaScript(url, controller.signal, 'x');
    const failed = expect(first.ready).rejects.toThrow('加载失败');
    await vi.advanceTimersByTimeAsync(10_000);
    await failed;
    const retry = acquireCaptchaScript(url, controller.signal, 'x');
    expect(appended).toHaveLength(2);
    const canceled = expect(retry.ready).rejects.toMatchObject({
      name: 'AbortError',
    });
    controller.abort();
    await canceled;
    expect(vi.getTimerCount()).toBe(0);
  });
});
