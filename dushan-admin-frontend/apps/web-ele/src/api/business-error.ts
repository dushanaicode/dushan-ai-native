import type { RequestClientConfig, RequestResponse } from '@vben/request';

import type { ApiResponse, ErrorDetails } from './response';

/** 保留业务码和公开详情，供认证与当前表单分别处理。 */
export class BusinessError extends Error {
  readonly code: number;
  readonly details: ErrorDetails | null;

  constructor(
    body: ApiResponse<unknown>,
    readonly config: RequestClientConfig,
    readonly response?: RequestResponse,
  ) {
    super(body.message);
    this.name = 'BusinessError';
    this.code = body.code;
    this.details = body.error;
  }
}

export function isDemoDenied(error: unknown): boolean {
  return error instanceof BusinessError && error.code === 901;
}
