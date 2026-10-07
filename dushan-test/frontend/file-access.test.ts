import { beforeEach, expect, it, vi } from 'vitest';

import { resolveFileUrl } from '../../dushan-admin-frontend/apps/web-ele/src/services/file/file-access';

const request = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock('#/api/request', () => ({ requestClient: request }));

beforeEach(() => {
  vi.resetAllMocks();
  vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:http://localhost/private');
  vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
});

it('公开URL原样交给浏览器，不触发带认证的请求', async () => {
  const signal = new AbortController().signal;
  const url = 'https://files.example.test/avatar.png';
  expect(await resolveFileUrl(url, signal)).toBe(url);
  expect(request.get).not.toHaveBeenCalled();
  expect(URL.createObjectURL).not.toHaveBeenCalled();
});

it('私有文件通过requestClient取Blob，释放作用域时撤销object URL', async () => {
  const controller = new AbortController();
  const blob = new Blob(['private content']);
  request.get.mockResolvedValue(blob);
  const url = '/admin-api/infra/file/private/123/folder/a%20b.pdf';
  expect(await resolveFileUrl(url, controller.signal)).toBe(
    'blob:http://localhost/private',
  );
  expect(request.get).toHaveBeenCalledWith(
    '/infra/file/private/123/folder/a%20b.pdf',
    expect.objectContaining({
      responseType: 'blob',
      responseReturn: 'body',
      signal: controller.signal,
    }),
  );
  expect(URL.createObjectURL).toHaveBeenCalledWith(blob);
  expect(URL.revokeObjectURL).not.toHaveBeenCalled();
  controller.abort();
  expect(URL.revokeObjectURL).toHaveBeenCalledExactlyOnceWith(
    'blob:http://localhost/private',
  );
});

it('组件已卸载时的迟到请求不能创建泄漏的object URL', async () => {
  const controller = new AbortController();
  const pending = Promise.withResolvers<Blob>();
  request.get.mockReturnValue(pending.promise);
  const result = resolveFileUrl(
    '/admin-api/infra/file/private/123/late.png',
    controller.signal,
  );
  const failure = expect(result).rejects.toMatchObject({ name: 'AbortError' });
  controller.abort();
  pending.resolve(new Blob(['late']));
  await failure;
  expect(URL.createObjectURL).not.toHaveBeenCalled();
});

it('鉴权失败直接传播，不回退到无认证的私有URL', async () => {
  const error = new Error('authentication failed');
  request.get.mockRejectedValue(error);
  await expect(
    resolveFileUrl(
      '/admin-api/infra/file/private/123/private.txt',
      new AbortController().signal,
    ),
  ).rejects.toBe(error);
  expect(URL.createObjectURL).not.toHaveBeenCalled();
});
