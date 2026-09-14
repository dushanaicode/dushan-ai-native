import type {
  CaptchaAnswer,
  CaptchaChallenge,
  CaptchaVerification,
} from './schema';

import { shallowRef } from 'vue';

import {
  captchaChallengeSchema,
  captchaConfigSchema,
  captchaVerificationSchema,
  parseCaptchaAnswer,
} from './schema';

export interface CaptchaPorts {
  configuration: (signal: AbortSignal) => Promise<unknown>;
  challenge: (purpose: string, signal: AbortSignal) => Promise<unknown>;
  check: (
    token: string,
    purpose: string,
    answer: CaptchaAnswer,
    signal: AbortSignal,
  ) => Promise<unknown>;
}

export class CaptchaController {
  get challenge() {
    return this.state.value.challenge;
  }
  get error() {
    return this.state.value.error;
  }
  get status() {
    return this.state.value.status;
  }
  private checking: Promise<CaptchaVerification> | undefined;
  private controller = new AbortController();
  private disposed = false;
  private expiresAt = 0;
  private expiry: ReturnType<typeof setTimeout> | undefined;

  private flow:
    | undefined
    | {
        purpose: string;
        resolve: (value: CaptchaVerification | null) => void;
        reject: (error: unknown) => void;
      };
  private operation = 0;
  private state = shallowRef<{
    challenge: CaptchaChallenge | null;
    error: unknown;
    status: 'error' | 'idle' | 'loading' | 'ready' | 'verified' | 'verifying';
  }>({ challenge: null, error: undefined, status: 'idle' });
  constructor(
    private readonly ports: CaptchaPorts,
    private readonly onError: (error: unknown) => void,
  ) {}

  acquire(purpose: string): Promise<CaptchaVerification | null> {
    if (this.disposed)
      return Promise.reject(
        new DOMException('验证码实例已关闭', 'InvalidStateError'),
      );
    this.cancel();
    const result = new Promise<CaptchaVerification | null>(
      (resolve, reject) => {
        this.flow = { purpose, resolve, reject };
      },
    );
    void this.reload().catch((error) => this.report(error));
    return result;
  }

  cancel() {
    this.operation += 1;
    this.controller.abort();
    clearTimeout(this.expiry);
    this.checking = undefined;
    this.flow?.reject(new DOMException('验证码已取消', 'AbortError'));
    this.flow = undefined;
    this.state.value = { challenge: null, status: 'idle', error: undefined };
  }

  dispose() {
    this.cancel();
    this.disposed = true;
  }

  async reload() {
    const flow = this.flow;
    if (!flow || this.disposed)
      throw new DOMException('没有进行中的验证', 'InvalidStateError');
    this.controller.abort();
    this.controller = new AbortController();
    this.checking = undefined;
    clearTimeout(this.expiry);
    const operation = ++this.operation;
    const signal = this.controller.signal;
    this.state.value = {
      ...this.state.value,
      challenge: null,
      status: 'loading',
    };
    try {
      const config = captchaConfigSchema.parse(
        await this.ports.configuration(signal),
      );
      this.assertCurrent(operation);
      if (!config.enabled) {
        this.state.value = {
          challenge: null,
          status: 'verified',
          error: undefined,
        };
        this.flow = undefined;
        flow.resolve(null);
        return;
      }
      if (!config.purposes.includes(flow.purpose))
        throw new TypeError('验证码用途未开放');
      const challenge = captchaChallengeSchema.parse(
        await this.ports.challenge(flow.purpose, signal),
      );
      this.assertCurrent(operation);
      if (
        challenge.purpose !== flow.purpose ||
        challenge.provider !== config.provider
      )
        throw new TypeError('验证码挑战与配置不一致');
      this.expiresAt = Date.now() + challenge.expires_in * 1000;
      this.state.value = { ...this.state.value, challenge, status: 'ready' };
      this.expiry = setTimeout(() => {
        void this.reload().catch((error) => this.report(error));
      }, challenge.expires_in * 1000);
    } catch (error) {
      this.assertCurrent(operation);
      this.state.value = { ...this.state.value, status: 'error', error };
      throw error;
    }
  }

  submit(value: unknown): Promise<CaptchaVerification> {
    if (this.checking) return this.checking;
    const challenge = this.challenge;
    const flow = this.flow;
    if (!challenge || !flow || this.disposed)
      return Promise.reject(
        new DOMException('验证码尚未就绪', 'InvalidStateError'),
      );
    if (Date.now() >= this.expiresAt) {
      void this.reload().catch((error) => this.report(error));
      return Promise.reject(new DOMException('验证码已过期', 'TimeoutError'));
    }
    const answer = parseCaptchaAnswer(challenge, value);
    clearTimeout(this.expiry);
    const operation = this.operation;
    this.state.value = {
      ...this.state.value,
      status: 'verifying',
      error: undefined,
    };
    const checking = this.ports
      .check(challenge.token, challenge.purpose, answer, this.controller.signal)
      .then((value) => {
        this.assertCurrent(operation);
        const verification = captchaVerificationSchema.parse(value);
        if (verification.purpose !== flow.purpose)
          throw new TypeError('验证码凭证用途不一致');
        this.state.value = { ...this.state.value, status: 'verified' };
        this.flow = undefined;
        flow.resolve(verification);
        return verification;
      })
      .catch(async (error: unknown) => {
        this.assertCurrent(operation);
        this.state.value = { ...this.state.value, status: 'error', error };

        try {
          await this.reload();
        } catch (reloadError) {
          this.report(reloadError);
        }
        throw error;
      })
      .finally(() => {
        if (this.checking === checking) this.checking = undefined;
      });
    this.checking = checking;
    return checking;
  }
  private assertCurrent(operation: number) {
    if (this.disposed || operation !== this.operation)
      throw new DOMException('验证码操作已失效', 'AbortError');
  }
  private report(error: unknown) {
    if (error instanceof DOMException && error.name === 'AbortError') return;
    this.onError(error);
  }
}
