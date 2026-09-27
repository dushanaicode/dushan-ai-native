import { expect, it, vi } from 'vitest';

const calls = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
}));
vi.mock('#/api/request', () => ({ requestClient: calls }));

import {
  createNotice,
  deleteNotice,
  deleteNoticeList,
  getNotice,
  getNoticePage,
  pushNoticeToTargets,
  updateNotice,
  updateNoticeStatus,
} from '../../dushan-admin-frontend/apps/web-ele/src/api/system/notification/notice';

it('通知 CRUD 和推送都使用当前后端 /system/notification 路由', async () => {
  const data = {
    title: '通知',
    content: '内容',
    channels: ['INTERNAL'],
    status: 1,
    type: 1,
    userType: 2,
  };
  await getNoticePage({ page: 1, pageSize: 20 });
  await getNotice('9007199254740993');
  await createNotice(data);
  await updateNotice({ ...data, id: '9007199254740993' });
  await updateNoticeStatus('9007199254740993', 0);
  await deleteNotice('9007199254740993');
  await deleteNoticeList(['9007199254740993']);
  await pushNoticeToTargets({
    id: '9007199254740993',
    userIds: ['9007199254740994'],
  });
  expect(calls.get.mock.calls.map((call) => call[0])).toEqual([
    '/system/notification/page',
    '/system/notification/get?id=9007199254740993',
  ]);
  expect(calls.post.mock.calls.map((call) => call[0])).toEqual([
    '/system/notification/create',
    '/system/notification/push-targets',
  ]);
  expect(calls.put.mock.calls.map((call) => call[0])).toEqual([
    '/system/notification/update',
    '/system/notification/update-status',
  ]);
  expect(calls.delete.mock.calls).toEqual([
    ['/system/notification/delete?id=9007199254740993'],
    [
      '/system/notification/delete-list',
      { params: { ids: ['9007199254740993'] }, paramsSerializer: 'repeat' },
    ],
  ]);
});
