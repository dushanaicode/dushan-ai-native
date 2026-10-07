import { expect, it, vi } from 'vitest';

import { testFileConfig } from '../../dushan-admin-frontend/apps/web-ele/src/api/infra/file-config';

const requests = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock('#/api/request', () => ({ requestClient: requests }));

it('文件配置探测使用 POST 且保留字符串 ID', async () => {
  requests.post.mockResolvedValue('https://storage.test/probe');
  expect(await testFileConfig('9223372036854775807')).toBe(
    'https://storage.test/probe',
  );
  expect(requests.post).toHaveBeenCalledWith(
    '/infra/file/config/test',
    undefined,
    { params: { id: '9223372036854775807' } },
  );
  expect(requests.get).not.toHaveBeenCalled();
});
