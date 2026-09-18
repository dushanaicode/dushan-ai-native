import type { RequestClientOptions } from '@vben/request';

import type { NativeRequestConfig } from './response';

import { useAppConfig } from '@vben/hooks';
import { preferences } from '@vben/preferences';
import { errorMessageResponseInterceptor, RequestClient } from '@vben/request';

import { ElMessage } from 'element-plus';

import { SessionChangedError } from '../services/session/coordinator';
import {
  configureSessionRequests,
  configureSessionStreaming,
} from '../services/session/http';
import { getSession } from '../services/session/runtime';
import { BusinessError } from './business-error';
import {
  configureNativeStreaming,
  isAuthenticationFailure,
  nativeResponseInterceptor,
} from './response';

const { apiURL } = useAppConfig(import.meta.env, import.meta.env.PROD);

function createRequestClient(baseURL: string, options?: RequestClientOptions) {
  const client = new RequestClient({ ...options, baseURL });
  const shownErrors = new WeakSet<object>();
  client.addRequestInterceptor({
    fulfilled(config) {
      config.headers['Accept-Language'] = preferences.app.locale;
      return config;
    },
  });
  configureSessionRequests(
    client,
    getSession,
    () => preferences.app.enableRefreshToken,
  );
  configureNativeStreaming(client);
  configureSessionStreaming(
    client,
    getSession,
    () => preferences.app.enableRefreshToken,
  );
  client.addResponseInterceptor(
    errorMessageResponseInterceptor((message, error) => {
      if (error instanceof SessionChangedError) return;
      if (
        isAuthenticationFailure(error) &&
        getSession().capture().token === null
      )
        return;
      if (
        error instanceof BusinessError &&
        (error.config as NativeRequestConfig).errorMessageMode === 'form'
      )
        return;
      if (typeof error === 'object' && error !== null) {
        if (shownErrors.has(error)) return;
        shownErrors.add(error);
      }
      ElMessage.error(error instanceof BusinessError ? error.message : message);
    }),
  );
  return client;
}

export const requestClient = createRequestClient(apiURL, {
  responseReturn: 'data',
});

// 认证端点使用相同 JSON 协议，但不进入自身的令牌刷新流程。
export const authenticationClient = new RequestClient({
  baseURL: apiURL,
  responseReturn: 'data',
});
authenticationClient.addResponseInterceptor(nativeResponseInterceptor());
