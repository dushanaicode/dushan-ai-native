import {
  createRouter,
  createWebHashHistory,
  createWebHistory,
} from 'vue-router';

import { cloneDeep } from '@vben/utils';

import { createRouterGuard } from './guard';
import { routes } from './routes';
import { reportNavigationFailure } from './session-access';

/**
 *  @zh_CN 创建vue-router实例
 */
const router = createRouter({
  history:
    import.meta.env.VITE_ROUTER_HISTORY === 'hash'
      ? createWebHashHistory(import.meta.env.VITE_BASE)
      : createWebHistory(import.meta.env.VITE_BASE),
  // 应该添加到路由的初始路由列表。
  routes: cloneDeep(routes),
  scrollBehavior: (to, _from, savedPosition) => {
    if (savedPosition) {
      return savedPosition;
    }
    return to.hash ? { behavior: 'smooth', el: to.hash } : { left: 0, top: 0 };
  },
  // 是否应该禁止尾部斜杠。
  // strict: true,
});

// 创建路由守卫
router.onError(reportNavigationFailure);
createRouterGuard(router);

export { router };
