import { requestClient } from '#/api/request';

export async function resolveFileUrl(
  url: string,
  signal: AbortSignal,
): Promise<string> {
  signal.throwIfAborted();
  if (!url.startsWith('/admin-api/infra/file/private/')) return url;

  const blob = await requestClient.get<Blob>(url.slice('/admin-api'.length), {
    responseReturn: 'body',
    responseType: 'blob',
    signal,
  });
  signal.throwIfAborted();
  const objectUrl = URL.createObjectURL(blob);
  signal.addEventListener('abort', () => URL.revokeObjectURL(objectUrl), {
    once: true,
  });
  return objectUrl;
}
