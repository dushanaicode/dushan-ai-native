import { $t } from '@vben/locales';
import { isAxiosError } from '@vben/request';

import { ElMessage } from 'element-plus';

import { SessionChangedError } from '../services/session/coordinator';
import { BusinessError } from './business-error';

const displayed = new WeakSet<object>();

/** 后端业务错误以公开 message 为准；无后端响应时由调用方提供本地说明。 */
export function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof BusinessError ? error.message : fallback;
}

/** 同一错误只由请求层或一个局部视图呈现，取消操作不提示。 */
export function takeErrorMessage(error: unknown, fallback: string): string {
  if (
    error instanceof SessionChangedError ||
    (error instanceof DOMException && error.name === 'AbortError') ||
    (isAxiosError(error) && error.code === 'ERR_CANCELED') ||
    error === 'cancel' ||
    error === 'close'
  )
    return '';
  if (typeof error === 'object' && error !== null) {
    if (displayed.has(error)) return '';
    displayed.add(error);
  }
  return getErrorMessage(error, fallback);
}

export function notifyError(error: unknown, fallback?: string): void {
  const message = takeErrorMessage(
    error,
    fallback ??
      (error instanceof Error
        ? error.message
        : $t('ui.fallback.http.internalServerError')),
  );
  if (message) ElMessage.error(message);
}
