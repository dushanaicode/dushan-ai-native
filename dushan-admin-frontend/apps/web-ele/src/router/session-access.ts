import type { Router, RouteRecordRaw } from 'vue-router';

import type {
  SessionCoordinator,
  SessionSnapshot,
} from '../services/session/coordinator';

import { cloneDeep } from '@vben/utils';

export function reportNavigationFailure() {
  // 路由错误可能携带请求凭据；不把原错误写入控制台。
  console.error('页面导航失败，请检查界面中的请求提示');
}

export function restoreBaseRoutes(router: Router, routes: RouteRecordRaw[]) {
  router.clearRoutes();
  for (const route of cloneDeep(routes)) router.addRoute(route);
}

export function scopedRouter(
  router: Router,
  assertCurrent: () => void,
): Router {
  return {
    ...router,
    getRoutes() {
      assertCurrent();
      return router.getRoutes();
    },
  };
}

export function installSessionAccess(options: {
  clear: () => void;
  onExternalChange: (snapshot: SessionSnapshot) => void;
  router: Router;
  routes: RouteRecordRaw[];
  session: SessionCoordinator;
}) {
  return options.session.subscribe((next, previous, source) => {
    if (next.generation === previous.generation) return;
    restoreBaseRoutes(options.router, options.routes);
    options.clear();
    if (source === 'external') options.onExternalChange(next);
  });
}

export function readRedirect(value: unknown, defaultPath: string) {
  if (value === undefined || value === null) return defaultPath;
  if (typeof value !== 'string') throw new TypeError('跳转地址必须是字符串');
  const path = decodeURIComponent(value);
  if (!path.startsWith('/') || path.startsWith('//') || path.includes('\\'))
    throw new TypeError('只允许应用内跳转');
  return path;
}
