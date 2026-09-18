import type { RequestClient } from '@vben/request';

import type { NativeRequestConfig } from '../../api/response';
import type { SessionCoordinator, SessionSnapshot } from './coordinator';

import {
  isAuthenticationFailure,
  nativeResponseInterceptor,
} from '../../api/response';

export function configureSessionRequests(
  client: RequestClient,
  getSession: () => SessionCoordinator,
  refreshEnabled: () => boolean,
) {
  client.addRequestInterceptor({
    fulfilled(config) {
      const session = getSession();
      const settings = config as NativeRequestConfig & typeof config;
      settings.__session = session.assertCurrent(
        settings.__session ?? session.capture(),
      );
      const token = settings.__session.token;
      config.headers.Authorization = token === null ? null : `Bearer ${token}`;
      return config;
    },
  });

  const native = nativeResponseInterceptor();
  client.addResponseInterceptor({
    async fulfilled(response) {
      const context = (response.config as NativeRequestConfig)
        .__session as SessionSnapshot;
      const session = getSession();
      session.assertCurrent(context);
      let value;
      try {
        value = await native.fulfilled(response);
      } catch (error) {
        session.assertCurrent(context);
        throw error;
      }
      session.assertCurrent(context);
      return value;
    },
  });
  client.addResponseInterceptor({
    async rejected(error) {
      const config = error.config as NativeRequestConfig | undefined;
      const session = getSession();
      if (config?.__session) session.assertCurrent(config.__session);
      if (!isAuthenticationFailure(error)) throw error;
      const settings = config as NativeRequestConfig & {
        __session: SessionSnapshot;
        url: string;
      };
      if (!refreshEnabled() || settings.__isRetryRequest) {
        await session.expire(settings.__session);
        throw error;
      }
      settings.__isRetryRequest = true;
      const token = await session.refresh(settings.__session);
      session.assertCurrent(settings.__session);
      const replay =
        settings.allowAuthReplay ??
        ['get', 'head', 'options'].includes(settings.method as string);
      if (!replay) throw error;
      settings.headers = {
        ...settings.headers,
        Authorization: `Bearer ${token}`,
      };
      return client.request(settings.url, settings);
    },
  });
}

export function configureSessionStreaming(
  client: RequestClient,
  getSession: () => SessionCoordinator,
  refreshEnabled: () => boolean,
) {
  const request = client.requestSSE;
  client.requestSSE = async (url, data, options) => {
    const session = getSession();
    const context = session.capture();
    const controller = new AbortController();
    const unsubscribe = session.subscribe((next) => {
      if (next.generation !== context.generation) controller.abort();
    });
    const signal = AbortSignal.any([
      session.signal,
      controller.signal,
      ...(options?.signal ? [options.signal] : []),
    ]);
    const attempt = () =>
      request(url, data, {
        ...options,
        signal,
        onEnd() {
          session.assertCurrent(context);
          options?.onEnd?.();
        },
        onMessage(chunk) {
          session.assertCurrent(context);
          options?.onMessage?.(chunk);
        },
        async onResponse(response) {
          session.assertCurrent(context);
          await options?.onResponse?.(response);
          session.assertCurrent(context);
        },
      });
    try {
      try {
        return await attempt();
      } catch (error) {
        // 流式请求不经 axios 响应拦截器；401 在此进入同一条刷新契约后重试一次，
        // 重试走请求拦截器自动携带新令牌（刷新不改代次，context 仍然有效）。
        // 401 有两种载体：传输层 status 字段与 200 响应体的 code 字段。
        if (
          !refreshEnabled() ||
          ((error as { status?: number }).status !== 401 &&
            !isAuthenticationFailure(error))
        ) {
          throw error;
        }
        await session.refresh(context);
        session.assertCurrent(context);
        return await attempt();
      }
    } finally {
      unsubscribe();
    }
  };
}
