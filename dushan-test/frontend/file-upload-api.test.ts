import type { InternalAxiosRequestConfig } from 'axios';

import { beforeEach, expect, it, vi } from 'vitest';

import {
  deleteByKeys,
  uploadBusinessFile,
  uploadFile,
} from '../../dushan-admin-frontend/apps/web-ele/src/api/infra/file';
import { importUser } from '../../dushan-admin-frontend/apps/web-ele/src/api/system/user';

const captured = vi.hoisted(() => ({
  requests: [] as InternalAxiosRequestConfig[],
  urls: [] as string[],
}));
vi.mock('#/api/request', async () => {
  const { RequestClient } = await import('@vben/request');
  const requestClient = new RequestClient({
    adapter: async (config) => {
      captured.requests.push(config);
      captured.urls.push(requestClient.instance.getUri(config));
      return {
        config,
        data: 'https://files.example.test/uploaded.txt',
        headers: {},
        status: 200,
        statusText: 'OK',
      };
    },
  });
  requestClient.addResponseInterceptor({
    fulfilled: (response) => response.data,
  });
  return { requestClient };
});

beforeEach(() => {
  captured.requests.length = 0;
  captured.urls.length = 0;
});

it('批量删除的重复Query参数保留逗号和首尾空格key', async () => {
  const keys = ['a,b.txt', ' leading-and-trailing ', 'one.txt'];
  await deleteByKeys('9223372036854775807', keys);
  const url = new URL(captured.urls[0], 'https://request.test');
  expect(url.pathname).toBe('/infra/file/delete-by-keys');
  expect(url.searchParams.get('configId')).toBe('9223372036854775807');
  expect(url.searchParams.getAll('keys')).toEqual(keys);
});

it('真实请求序列化保留文件二进制、目录和字符串存储ID', async () => {
  const file = new File(['真实上传内容'], '说明.txt', { type: 'text/plain' });
  expect(await uploadFile(file, 'public', '资料/2026/', '9223372036854775807')).toBe(
    'https://files.example.test/uploaded.txt',
  );
  const request = captured.requests[0];
  expect(request.url).toBe('/infra/file/upload');
  expect(request.headers.getContentType()).toContain('multipart/form-data');
  expect(request.data).toBeInstanceOf(FormData);
  expect(request.data.get('file')).toBe(file);
  expect(request.data.get('directory')).toBe('资料/2026/');
  expect(request.data.get('configId')).toBe('9223372036854775807');
  expect(request.data.get('visibility')).toBe('public');
});

it('默认存储上传省略可选字段，不发送undefined或空ID', async () => {
  const file = new File(['content'], 'demo.txt', { type: 'text/plain' });
  await uploadFile(file, 'private');
  const request = captured.requests[0];
  expect(request.data).toBeInstanceOf(FormData);
  expect([...request.data.keys()]).toEqual(['file', 'visibility']);
  expect(request.data.get('visibility')).toBe('private');
});

it.each(['avatar', 'logo', 'form-image', 'form-file'] as const)(
  '业务上传只提交文件和用途 %s，并传递取消信号',
  async (usage) => {
    const file = new File(['content'], 'demo.png', { type: 'image/png' });
    const controller = new AbortController();
    await uploadBusinessFile(file, usage, controller.signal);
    const request = captured.requests[0];
    expect(request.url).toBe('/infra/file/business-upload');
    expect(request.signal).toBe(controller.signal);
    expect(request.data.get('file')).toBe(file);
    expect(request.data.get('usage')).toBe(usage);
    expect([...request.data.keys()].sort()).toEqual(['file', 'usage']);
  },
);

it.each([false, true])(
  '用户导入使用 multipart 保留文件，更新开关为 %s',
  async (updateSupport) => {
    const file = new File(['workbook'], 'users.xlsx');
    await importUser(file, updateSupport);
    const request = captured.requests[0];
    expect(request.url).toBe('/system/user/import');
    expect(request.headers.getContentType()).toContain('multipart/form-data');
    expect(request.data).toBeInstanceOf(FormData);
    expect(request.data.get('file')).toBe(file);
    expect(request.data.get('updateSupport')).toBe(String(updateSupport));
  },
);
