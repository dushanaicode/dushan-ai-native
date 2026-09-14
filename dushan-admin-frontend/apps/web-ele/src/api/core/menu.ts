import { requestClient } from '#/api/request';

import { parseMenus } from '../../router/menu-adapter';

/**
 * 获取用户所有菜单
 */
export async function getAllMenusApi() {
  return parseMenus(await requestClient.get<unknown>('/menu/all'));
}
