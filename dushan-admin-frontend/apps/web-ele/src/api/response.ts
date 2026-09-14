import type {
  RequestClient,
  RequestClientConfig,
  RequestResponse,
} from '@vben/request';

import type { SessionSnapshot } from '../services/session/coordinator';

import { isAxiosError } from '@vben/request';

import { BusinessError } from './business-error';

export interface FieldError {
  field: string;
  message: string;
}

export interface ErrorDetails {
  fields?: FieldError[];
  retryable?: boolean;
  retryAfter?: number;
  debug?: Record<string, unknown>;
}

export interface ApiResponse<T> {
  code: number;
  message: string;
  data: null | T;
  error: ErrorDetails | null;
}

export interface PageQuery {
  page: number;
  pageSize: number;
}

export interface PageResult<T> {
  items: T[];
  total: number;
}

export type NativeRequestConfig = {
  /** 只在客户端保存会话上下文，不发送为请求头。 */
  __session?: SessionSnapshot;
  __isRetryRequest?: boolean;
  /** GET/HEAD/OPTIONS 默认可重放，写请求须由调用方明确允许。 */
  allowAuthReplay?: boolean;
  /** form只将业务错误交给提交表单，网络故障仍由请求层提示。 */
  errorMessageMode?: 'form' | 'message';
} & RequestClientConfig;

/** 校验外部响应的固定协议，缺字段或类型错误直接报告协议故障。 */
export function parseApiResponse(value: unknown): ApiResponse<unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new TypeError('接口返回格式不符合约定');
  }
  const body = value as Record<string, unknown>;
  if (
    !Number.isInteger(body.code) ||
    typeof body.message !== 'string' ||
    !Object.hasOwn(body, 'data') ||
    !Object.hasOwn(body, 'error')
  ) {
    throw new TypeError('接口返回格式不符合约定');
  }
  const details = body.error;
  if (details !== null) {
    if (typeof details !== 'object' || Array.isArray(details)) {
      throw new TypeError('接口错误详情必须是对象或null');
    }
    const { fields } = details as Record<string, unknown>;
    if (
      fields !== undefined &&
      (!Array.isArray(fields) ||
        !fields.every(
          (item: unknown) =>
            typeof item === 'object' &&
            item !== null &&
            typeof (item as FieldError).field === 'string' &&
            typeof (item as FieldError).message === 'string',
        ))
    ) {
      throw new TypeError('接口字段错误详情不符合约定');
    }
  }
  return body as unknown as ApiResponse<unknown>;
}

/** 对普通业务JSON解包一次，保留文件下载等body/raw调用方式。 */
export function nativeResponseInterceptor() {
  return {
    async fulfilled(response: RequestResponse) {
      // 文件失败是JSON且没有下载头，不能把业务错误保存为一个下载文件。
      const mediaType = String(response.headers['content-type'] ?? '')
        .split(';')[0]
        ?.trim()
        .toLowerCase();
      if (
        response.config.responseType === 'blob' &&
        mediaType === 'application/json' &&
        !response.headers['content-disposition']
      ) {
        const body = parseApiResponse(
          JSON.parse(await (response.data as Blob).text()),
        );
        if (body.code !== 0)
          throw new BusinessError(body, response.config, response);
        throw Object.assign(
          new Error('下载接口返回了JSON成功体，缺少文件内容'),
          { config: response.config, response },
        );
      }
      if (response.config.responseReturn === 'raw') return response;
      if (response.config.responseReturn === 'body') return response.data;
      let body: ApiResponse<unknown>;
      try {
        body = parseApiResponse(response.data);
      } catch (error) {
        throw Object.assign(error as Error, {
          config: response.config,
          response,
        });
      }
      if (body.code === 0) return body.data;
      throw new BusinessError(body, response.config, response);
    },
  };
}

/** 识别业务码和 HTTP 401，认证端点不递归刷新。 */
export function isAuthenticationFailure(error: unknown): boolean {
  if (!(error instanceof BusinessError) && !isAxiosError(error)) return false;
  return (
    (error instanceof BusinessError ? error.code : error.response?.status) ===
      401 &&
    !/\/auth\/(?:login|logout|refresh)(?:[/?]|$)/.test(error.config?.url ?? '')
  );
}

/** 为底层SSE请求安装协议检查，错误继续通过Promise交给调用方处理。 */
export function configureNativeStreaming(client: RequestClient): void {
  const requestSSE = client.requestSSE;
  client.requestSSE = (url, data, options) =>
    requestSSE(url, data, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...Object.fromEntries(new Headers(options?.headers).entries()),
      },
      async onResponse(response) {
        const mediaType = response.headers
          .get('content-type')
          ?.split(';')[0]
          ?.trim()
          .toLowerCase();
        if (mediaType === 'application/json') {
          const body = parseApiResponse(await response.json());
          if (body.code !== 0)
            throw new BusinessError(body, {
              url,
              method: options?.method ?? 'GET',
            });
          throw new Error('SSE接口返回了JSON成功体，缺少事件流');
        }
        if (mediaType !== 'text/event-stream')
          throw new Error('SSE接口返回了不支持的媒体类型');
        await options?.onResponse?.(response);
      },
    });
  client.postSSE = (url, data, options) =>
    client.requestSSE(url, data, { ...options, method: 'POST' });
}
