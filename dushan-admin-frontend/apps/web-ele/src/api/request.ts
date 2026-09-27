import type { RequestClientOptions } from '@vben/request';

import type { NativeRequestConfig } from './response';

import { useAppConfig } from '@vben/hooks';
import { preferences } from '@vben/preferences';
import { errorMessageResponseInterceptor, RequestClient } from '@vben/request';

import { SessionChangedError } from '../services/session/coordinator';
import {
  configureSessionRequests,
  configureSessionStreaming,
} from '../services/session/http';
import { getSession } from '../services/session/runtime';
import { BusinessError } from './business-error';
import { notifyError } from './error-feedback';
import {
  configureNativeStreaming,
  isAuthenticationFailure,
  nativeResponseInterceptor,
} from './response';

const { apiURL } = useAppConfig(import.meta.env, import.meta.env.PROD);

function createRequestClient(
  baseURL: string,
  options?: RequestClientOptions,
  withSession = true,
) {
  const client = new RequestClient({ ...options, baseURL });
  client.addRequestInterceptor({
    fulfilled(config) {
      config.headers['Accept-Language'] = preferences.app.locale;
      return config;
    },
  });
  if (withSession) {
    configureSessionRequests(
      client,
      getSession,
      () => preferences.app.enableRefreshToken,
    );
  } else {
    client.addResponseInterceptor(nativeResponseInterceptor());
  }
  configureNativeStreaming(client);
  if (withSession) {
    configureSessionStreaming(
      client,
      getSession,
      () => preferences.app.enableRefreshToken,
    );
  }
  client.addResponseInterceptor(
    errorMessageResponseInterceptor((message, error) => {
      if (error instanceof SessionChangedError) return;
      if (
        withSession &&
        isAuthenticationFailure(error) &&
        getSession().capture().token === null
      )
        return;
      if (
        error instanceof BusinessError &&
        (error.config as NativeRequestConfig).errorMessageMode === 'form'
      )
        return;
      notifyError(error, message);
    }),
  );
  return client;
}

export const requestClient = createRequestClient(apiURL, {
  responseReturn: 'data',
});

export const anonymousClient = createRequestClient(
  apiURL,
  { responseReturn: 'data' },
  false,
);

// 认证端点使用相同 JSON 协议，但不进入自身的令牌刷新流程。
export const authenticationClient = new RequestClient({
  baseURL: apiURL,
  responseReturn: 'data',
});
authenticationClient.addResponseInterceptor(nativeResponseInterceptor());
