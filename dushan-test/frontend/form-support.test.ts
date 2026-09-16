import { describe, expect, it, vi } from 'vitest';

import {
  generateCron,
  parseCron,
} from '../../dushan-admin-frontend/apps/web-ele/src/components/cron-tab/cron';
import { uploadCroppedAvatar } from '../../dushan-admin-frontend/apps/web-ele/src/components/upload/avatar';
import {
  fileIds,
  parseFileAccess,
  UploadQueue,
  validateFile,
} from '../../dushan-admin-frontend/apps/web-ele/src/components/upload/files';
import {
  parseSelected,
  parseUsers,
  selectionValue,
  toggleUser,
  userIds,
} from '../../dushan-admin-frontend/apps/web-ele/src/components/user-select/selection';

const descriptor = {
  id: '18446744073709551615',
  name: 'avatar.png',
  size: 2,
  mediaType: 'image/png',
};
const file = () => new File(['ok'], 'avatar.PNG', { type: 'image/png' });
const limits = { accept: '.png,image/jpeg', maxSize: 1, maxNumber: 3 };

describe('cron生成和解析', () => {
  it.each([
    '* * * * *',
    '0 0 * * 0',
    '*/5 1-23 1,15 1-12 0-6',
    '0/10 12 31 12 6',
    '59 23 1 1 0',
  ])('五段表达式往返不损失语义：%s', (value) => {
    expect(generateCron(parseCron(value))).toBe(value);
  });
  it.each([
    '0 0 0 * * *',
    '60 * * * *',
    '* 24 * * *',
    '* * 0 * *',
    '* * * 13 *',
    '* * * * 7',
    '*/0 * * * *',
    '5-1 * * * *',
    '1x * * * *',
    '1,,2 * * * *',
  ])('拒绝截断、越界和部分数字：%s', (value) => {
    expect(() => parseCron(value)).toThrow();
  });
  it('空指定列表不可退回任意值', () => {
    const fields = parseCron('* * * * *');
    fields[0] = { mode: 'list', values: [] };
    expect(() => generateCron(fields)).toThrow();
  });
});

describe('文件上传与头像', () => {
  function setup() {
    const upload = vi.fn(async () => descriptor);
    const write = vi.fn();
    const queue = new UploadQueue({
      ports: () => ({ upload, resolve: async () => [] }),
      limits: () => limits,
      write,
    });
    return { queue, upload, write };
  }
  it('校验扩展名、MIME、大小和数量，在请求前拒绝超限', async () => {
    expect(() => validateFile(file(), limits)).not.toThrow();
    expect(() =>
      validateFile(
        new File(['x'], 'file.exe', { type: 'application/octet-stream' }),
        limits,
      ),
    ).toThrow('类型');
    expect(() =>
      validateFile(
        new File([new Uint8Array(1024 * 1024 + 1)], 'file.png'),
        limits,
      ),
    ).toThrow('大小');
    const { queue, upload } = setup();
    queue.sync(['a', 'b', 'c']);
    await expect(queue.add([file()])).rejects.toThrow('数量');
    expect(upload).not.toHaveBeenCalled();
    queue.dispose();
  });
  it('进度包括0；模型只写字符串ID，临时访问URL只存在解析结果中', async () => {
    const write = vi.fn();
    const upload = vi.fn(async (_file, { onProgress }) => {
      onProgress(0);
      onProgress(51);
      return descriptor;
    });
    const queue = new UploadQueue({
      ports: () => ({ upload, resolve: async () => [] }),
      limits: () => limits,
      write,
    });
    await queue.add([file()]);
    expect(write).toHaveBeenCalledWith([descriptor.id]);
    expect(queue.ids).toEqual([descriptor.id]);
    const access = parseFileAccess(
      [{ ...descriptor, url: '/files/access?ticket=temporary' }],
      [descriptor.id],
    );
    expect(access[0]?.url).toContain('ticket=temporary');
    expect(JSON.stringify(write.mock.calls)).not.toContain('temporary');
    queue.remove(descriptor.id);
    expect(write).toHaveBeenLastCalledWith([]);
    queue.dispose();
  });
  it('失败保留已有值，已成功项不回滚；失败项不进入模型', async () => {
    const { queue, upload, write } = setup();
    const failure = new Error('upload failed');
    queue.sync(['existing']);
    upload.mockResolvedValueOnce(descriptor).mockRejectedValueOnce(failure);
    await expect(queue.add([file(), file()])).rejects.toBe(failure);
    expect(queue.ids).toEqual(['existing', descriptor.id]);
    expect(queue.jobs).toEqual([]);
    expect(write).toHaveBeenCalledTimes(1);
    queue.dispose();
  });
  it('取消与外部值重置不接纳迟到响应，重复请求占用数量额度', async () => {
    const { queue, upload, write } = setup();
    const pending = Promise.withResolvers<typeof descriptor>();
    upload.mockReturnValueOnce(pending.promise);
    const request = queue.add([file()]);
    const key = queue.jobs[0]!.key;
    queue.cancel(key);
    pending.resolve(descriptor);
    await request;
    expect(write).not.toHaveBeenCalled();
    expect(queue.jobs).toEqual([]);
    const next = Promise.withResolvers<typeof descriptor>();
    upload.mockReturnValueOnce(next.promise);
    const second = queue.add([file()]);
    queue.sync(['new-form']);
    next.resolve(descriptor);
    await second;
    expect(queue.ids).toEqual(['new-form']);
    expect(write).not.toHaveBeenCalled();
    queue.dispose();
  });
  it('文件访问严格匹配请求ID并拒绝可执行协议和URL凭据', () => {
    expect(fileIds(descriptor.id)).toEqual([descriptor.id]);
    expect(() => fileIds(123 as never)).toThrow();
    expect(() =>
      parseFileAccess(
        [{ ...descriptor, url: 'javascript:alert(1)' }],
        [descriptor.id],
      ),
    ).toThrow();
    expect(() =>
      parseFileAccess(
        [{ ...descriptor, url: 'https://user:secret@example.test' }],
        [descriptor.id],
      ),
    ).toThrow();
    expect(() => parseFileAccess([], [descriptor.id])).toThrow('不一致');
  });
  it('头像只上传有效裁剪Blob，输出文件ID；空输出失败', async () => {
    const controller = new AbortController();
    const upload = vi.fn(async () => descriptor);
    const cropper = {
      getCropImage: vi.fn(async () => new Blob(['ok'], { type: 'image/png' })),
    };
    await expect(
      uploadCroppedAvatar({
        cropper,
        ports: { upload },
        maxSize: 5,
        signal: controller.signal,
      }),
    ).resolves.toEqual(descriptor);
    expect(cropper.getCropImage).toHaveBeenCalledWith(
      'image/png',
      0.92,
      'blob',
      240,
      240,
    );
    expect(upload.mock.calls[0]![0]).toMatchObject({
      name: 'avatar.png',
      type: 'image/png',
    });
    cropper.getCropImage.mockResolvedValueOnce(new Blob());
    await expect(
      uploadCroppedAvatar({
        cropper,
        ports: { upload },
        maxSize: 5,
        signal: controller.signal,
      }),
    ).rejects.toThrow('有效图片');
    expect(upload).toHaveBeenCalledOnce();
  });
  it('裁剪期间取消不会开始上传，上传期间取消不返回持久值', async () => {
    const controller = new AbortController();
    const pending = Promise.withResolvers<Blob>();
    const upload = vi.fn(async () => descriptor);
    const result = uploadCroppedAvatar({
      cropper: { getCropImage: () => pending.promise },
      ports: { upload },
      maxSize: 5,
      signal: controller.signal,
    });
    controller.abort();
    pending.resolve(new Blob(['ok']));
    await expect(result).rejects.toMatchObject({ name: 'AbortError' });
    expect(upload).not.toHaveBeenCalled();
    const next = new AbortController();
    const uploaded = Promise.withResolvers<typeof descriptor>();
    upload.mockReturnValueOnce(uploaded.promise);
    const late = uploadCroppedAvatar({
      cropper: { getCropImage: async () => new Blob(['ok']) },
      ports: { upload },
      maxSize: 5,
      signal: next.signal,
    });
    await vi.waitFor(() => expect(upload).toHaveBeenCalledOnce());
    next.abort();
    uploaded.resolve(descriptor);
    await expect(late).rejects.toMatchObject({ name: 'AbortError' });
  });
});

describe('用户选择值契约', () => {
  it('超大ID和0字符串往返，单选/多选和清空行为明确', () => {
    const ids = userIds([descriptor.id, '0']);
    expect(selectionValue(ids, true)).toEqual(ids);
    expect(selectionValue(toggleUser(ids, 'next', false), false)).toBe('next');
    expect(toggleUser(ids, '0', true)).toEqual([descriptor.id]);
    expect(selectionValue([], false)).toBeUndefined();
    expect(() => userIds(123 as never)).toThrow();
    expect(() => userIds(['x', 'x'])).toThrow();
  });
  it('分页使用items/total，所选项必须完整且不能重复', () => {
    const user = { id: descriptor.id, label: '成员' };
    expect(parseUsers({ items: [user], total: 1 }).items[0]?.id).toBe(
      descriptor.id,
    );
    expect(parseSelected([user], [descriptor.id])).toEqual([user]);
    expect(() => parseSelected([], [descriptor.id])).toThrow();
    expect(() => parseUsers({ list: [user], total: 1 })).toThrow();
  });
});
