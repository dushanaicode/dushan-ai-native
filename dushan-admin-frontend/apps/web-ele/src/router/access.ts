import type {
  ComponentRecordType,
  GenerateMenuAndRoutesOptions,
} from '@vben/types';

import { generateAccessible } from '@vben/access';
import { preferences } from '@vben/preferences';

import { BasicLayout, IFrameView } from '#/layouts';
import { useAuthStore } from '#/store';

import { getSession } from '../services/session/runtime';
import { menusToRoutes } from './menu-adapter';
import { scopedRouter } from './session-access';

const forbiddenComponent = () => import('#/views/_core/fallback/forbidden.vue');

async function generateAccess(options: GenerateMenuAndRoutesOptions) {
  const session = getSession();
  const scope = session.capture();
  const pageMap: ComponentRecordType = import.meta.glob('../views/**/*.vue');

  const layoutMap: ComponentRecordType = {
    BasicLayout,
    IFrameView,
    RouterView: () => import('vue-router').then((module) => module.RouterView),
    ExternalLinkView: () => import('../layouts/external-link.vue'),
  };

  return await generateAccessible(preferences.app.accessMode, {
    ...options,
    router: scopedRouter(options.router, () => session.assertCurrent(scope)),
    // 菜单与身份来自同一次 /system/auth/get-permission-info，由 auth store 按代次持有。
    fetchMenuListAsync: async () => {
      const menus = useAuthStore().requireAccessMenus();
      session.assertCurrent(scope);
      return menusToRoutes(
        menus,
        pageMap,
        layoutMap,
        new Set(options.router.getRoutes().map((route) => route.path)),
      );
    },
    // 可以指定没有权限跳转403页面
    forbiddenComponent,
    // 如果 route.meta.menuVisibleWithForbidden = true
    layoutMap,
    pageMap,
  });
}

export { generateAccess };
