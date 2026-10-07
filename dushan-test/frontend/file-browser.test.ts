import { createApp, effectScope, nextTick } from 'vue';

import { afterEach, beforeEach, expect, it, vi } from 'vitest';

import { BusinessError } from '../../dushan-admin-frontend/apps/web-ele/src/api/business-error';
import FileListView from '../../dushan-admin-frontend/apps/web-ele/src/components/file-browser/components/file-list-view.vue';
import { useFileBrowser } from '../../dushan-admin-frontend/apps/web-ele/src/components/file-browser/use-file-browser';

const api = vi.hoisted(() => ({
  configs: vi.fn(),
  list: vi.fn(),
  search: vi.fn(),
  upload: vi.fn(),
  create: vi.fn(),
  remove: vi.fn(),
  removeMany: vi.fn(),
  rename: vi.fn(),
}));
vi.mock('@vben/icons', () => ({ IconifyIcon: { render: () => null } }));
vi.mock('#/api/infra/file', () => ({
  listObjects: api.list,
  searchFiles: api.search,
  uploadFile: api.upload,
  createDirectory: api.create,
  deleteByKey: api.remove,
  deleteByKeys: api.removeMany,
  renameFile: api.rename,
}));
vi.mock('#/api/infra/file-config', () => ({
  getSimpleFileConfigList: api.configs,
}));
const scopes: ReturnType<typeof effectScope>[] = [];
function browser() {
  const scope = effectScope();
  scopes.push(scope);
  return scope.run(useFileBrowser)!;
}
beforeEach(() => {
  vi.resetAllMocks();
  api.configs.mockResolvedValue([
    { id: '1', name: '数据库', storage: 1, master: true },
    { id: '2', name: 'MinIO', storage: 20, master: false },
  ]);
  api.list.mockResolvedValue({ objects: [], isTruncated: false });
});
afterEach(() => scopes.splice(0).forEach((scope) => scope.stop()));

it('切换空间取消旧请求，迟到结果不能覆盖新空间或目录', async () => {
  const state = browser();
  await state.loadConfigList();
  const old = Promise.withResolvers<{
    objects: { key: string; name: string }[];
  }>();
  api.list.mockReturnValueOnce(old.promise);
  const pending = state.navigateTo('old/');
  const signal = api.list.mock.calls.at(-1)![1].signal as AbortSignal;
  api.list.mockResolvedValueOnce({
    objects: [{ key: 'new.txt', name: 'new.txt' }],
  });
  await state.handleConfigChange('2');
  expect(signal.aborted).toBe(true);
  old.resolve({ objects: [{ key: 'old/stale.txt', name: 'stale.txt' }] });
  await pending;
  expect(state.configId.value).toBe('2');
  expect(state.currentPrefix.value).toBe('');
  expect(state.objects.value.map((item) => item.key)).toEqual(['new.txt']);
});

it('加载失败保留后端原文，不能显示为空目录；重试恢复', async () => {
  const state = browser();
  api.list.mockRejectedValueOnce(
    new BusinessError(
      { code: 400, message: '指定存储桶不存在', data: null, error: null },
      {},
    ),
  );
  await state.loadConfigList();
  expect(state.loadFailed.value).toBe(true);
  expect(state.errorMessage.value).toBe('指定存储桶不存在');
  expect(api.list.mock.calls[0]![1].errorMessageMode).toBe('form');
  await state.refresh();
  expect(state.loadFailed.value).toBe(false);
  expect(state.errorMessage.value).toBe('');
});

it('上传固定使用发起时的空间，切换后完成不会刷新错误位置', async () => {
  const state = browser();
  await state.loadConfigList();
  await state.navigateTo('docs/');
  const uploaded = Promise.withResolvers<string>();
  api.upload.mockReturnValueOnce(uploaded.promise);
  const file = new File(['file'], 'file.txt');
  const pending = state.handleUploadFile(file);
  expect(state.uploading.value).toBe(1);
  expect(api.upload).toHaveBeenCalledWith(file, 'private', 'docs/', '1');
  await state.handleConfigChange('2');
  const requests = api.list.mock.calls.length;
  uploaded.resolve('https://files.example.test/file.txt');
  await pending;
  expect(state.uploading.value).toBe(0);
  expect(state.configId.value).toBe('2');
  expect(api.list).toHaveBeenCalledTimes(requests);
});

it('管理上传显式携带用户选择的公开可见性', async () => {
  const state = browser();
  await state.loadConfigList();
  expect(state.uploadVisibility.value).toBe('private');
  state.uploadVisibility.value = 'public';
  const file = new File(['public'], 'public.txt');
  await state.handleUploadFile(file);
  expect(api.upload).toHaveBeenCalledWith(file, 'public', undefined, '1');
});

it('目录始终排在文件前，名称和大小排序不修改原列表', async () => {
  const state = browser();
  await state.loadConfigList();
  state.objects.value = [
    { key: 'z.txt', name: 'z.txt', size: 20 },
    { key: 'a.txt', name: 'a.txt', size: 1 },
    { key: 'docs/', name: 'docs', isDirectory: true },
  ];
  expect(state.sortedObjects.value.map((item) => item.key)).toEqual([
    'docs/',
    'a.txt',
    'z.txt',
  ]);
  state.sortBy.value = 'size';
  expect(state.sortedObjects.value.map((item) => item.key)).toEqual([
    'docs/',
    'z.txt',
    'a.txt',
  ]);
  expect(state.objects.value[0]!.key).toBe('z.txt');
});

it('归一后的FTP时间在实际列表中显示并按真实时刻排序', async () => {
  const state = browser();
  await state.loadConfigList();
  const stamp = '2026-09-26T01:02:03.125000+00:00';
  api.list.mockResolvedValueOnce({
    objects: [
      { key: 'unknown.txt', name: 'unknown.txt', lastModified: null },
      {
        key: 'older.txt',
        name: 'older.txt',
        lastModified: '2026-09-26T01:02:03+00:00',
      },
      { key: 'fraction.txt', name: 'fraction.txt', lastModified: stamp },
    ],
  });
  await state.refresh();
  state.sortBy.value = 'modified';
  expect(state.sortedObjects.value.map((item) => item.key)).toEqual([
    'fraction.txt',
    'older.txt',
    'unknown.txt',
  ]);
  const host = document.createElement('div');
  document.body.append(host);
  const app = createApp(FileListView, {
    objects: state.sortedObjects.value,
    selectedKeys: [],
  });
  try {
    app.mount(host);
    await nextTick();
    const rendered = [
      ...host.querySelectorAll('.file-list__row .file-list__cell--time'),
    ].map((cell) => cell.textContent?.trim());
    expect(rendered).toEqual([
      new Date('2026-09-26T01:02:03.125Z').toLocaleString('zh-CN'),
      new Date('2026-09-26T01:02:03Z').toLocaleString('zh-CN'),
      '-',
    ]);
    expect(host.textContent).not.toContain('Invalid Date');
  } finally {
    app.unmount();
    host.remove();
  }
});
