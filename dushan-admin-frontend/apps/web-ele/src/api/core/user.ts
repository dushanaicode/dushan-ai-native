import type { UserInfo } from '@vben/types';

import { requestClient } from '#/api/request';

import { readRedirect } from '../../router/session-access';

/**
 * 获取用户信息
 */
export async function getUserInfoApi() {
  const user = await requestClient.get<UserInfo>('/user/info');
  if (typeof user.userId !== 'string' || user.userId.length === 0)
    throw new TypeError('用户 ID 必须是非空字符串');
  if (typeof user.homePath !== 'string' || !user.homePath.startsWith('/'))
    throw new TypeError('用户信息缺少可达首页');
  readRedirect(user.homePath, '');
  return user;
}
