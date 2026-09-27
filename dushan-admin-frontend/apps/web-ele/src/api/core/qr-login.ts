import { z } from '@vben/common-ui';

import { anonymousClient, requestClient } from '#/api/request';

const path = '/system/auth/qr-login';
const options = { withCredentials: true };
const status = z.enum([
  'waiting',
  'scanned',
  'approved',
  'cancelled',
  'expired',
]);
const created = z.object({
  ticket: z.string().regex(/^[\w-]{43}$/),
  code: z.string().regex(/^\d{6}$/),
  tenantId: z.string().regex(/^[1-9]\d{0,18}$/),
  expiresAt: z.number(),
  pollInterval: z.number().int().positive(),
});
const scanned = created.omit({ ticket: true, pollInterval: true }).extend({
  status,
  browser: z.string(),
  ip: z.string(),
});

export type QrLoginTicket = z.infer<typeof created>;
export type QrLoginScan = z.infer<typeof scanned>;
export type QrLoginStatus = z.infer<typeof status>;

let enabledRequest: Promise<boolean> | undefined;
export function isQrLoginEnabled(): Promise<boolean> {
  if (import.meta.env.VITE_APP_QR_LOGIN_ENABLE !== 'true')
    return Promise.resolve(false);
  enabledRequest ??= anonymousClient
    .get(`${path}/enabled`)
    .then((value) => z.boolean().parse(value))
    .catch((error) => {
      enabledRequest = undefined;
      throw error;
    });
  return enabledRequest;
}

export async function createQrLogin(tenantId?: string) {
  return created.parse(
    await anonymousClient.post(
      `${path}/create`,
      {},
      {
        ...options,
        headers: tenantId === undefined ? {} : { 'X-Tenant-Id': tenantId },
      },
    ),
  );
}

export async function pollQrLogin(ticket: string, signal?: AbortSignal) {
  return z
    .object({ status })
    .parse(
      await anonymousClient.post(
        `${path}/poll`,
        { ticket },
        { ...options, signal },
      ),
    );
}

export async function consumeQrLogin(ticket: string) {
  return z
    .object({ accessToken: z.string().min(1), tenantId: z.string().min(1) })
    .parse(await anonymousClient.post(`${path}/consume`, { ticket }, options));
}

export async function cancelQrLogin(ticket: string) {
  await anonymousClient.post(`${path}/cancel`, { ticket }, options);
}

export async function scanQrLogin(ticket: string) {
  return scanned.parse(await requestClient.post(`${path}/scan`, { ticket }));
}

export async function confirmQrLogin(ticket: string, approve: boolean) {
  await requestClient.post(`${path}/confirm`, { ticket, approve });
}
