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
) {
  const request = client.requestSSE;
  client.requestSSE = async (url, data, options) => {
    const session = getSession();
    const context = session.capture();
    const controller = new AbortController();
    const unsubscribe = session.subscribe((next) => {
      if (next.generation !== context.generation) controller.abort();
    });
    try {
      return await request(url, data, {
        ...options,
        signal: AbortSignal.any([
          session.signal,
          controller.signal,
          ...(options?.signal ? [options.signal] : []),
        ]),
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
    } finally {
      unsubscribe();
    }
  };
}
