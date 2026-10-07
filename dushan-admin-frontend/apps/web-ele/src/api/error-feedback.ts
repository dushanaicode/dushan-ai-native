import type { App } from 'vue';

import { $t } from '@vben/locales';
import { isAxiosError } from '@vben/request';

import { ElMessage } from 'element-plus';

import { SessionChangedError } from '../services/session/coordinator';
import { BusinessError, isDemoDenied } from './business-error';

const displayed = new WeakSet<object>();

/** 后端业务错误以公开 message 为准；无后端响应时由调用方提供本地说明。 */
export function getErrorMessage(error: unknown, fallback: string): string {
  if (isDemoDenied(error)) return $t('readonlyDemo.denied');
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
  if (message) {
    if (isDemoDenied(error)) ElMessage.warning(message);
    else ElMessage.error(message);
  }
}

/** 请求仍拒绝以终止成功流程；只在最终 UI 边界消费已说明的只读拒绝。 */
export function installDemoErrorBoundary(app: App): () => void {
  const previous = app.config.errorHandler;
  app.config.errorHandler = (error, instance, info) => {
    if (isDemoDenied(error)) {
      notifyError(error);
    } else if (previous) {
      previous(error, instance, info);
    } else {
      throw error;
    }
  };
  const onUnhandledRejection = (event: PromiseRejectionEvent) => {
    if (!isDemoDenied(event.reason)) return;
    notifyError(event.reason);
    event.preventDefault();
  };
  window.addEventListener('unhandledrejection', onUnhandledRejection);
  return () => {
    app.config.errorHandler = previous;
    window.removeEventListener('unhandledrejection', onUnhandledRejection);
  };
}
