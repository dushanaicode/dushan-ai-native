import { createApp, watchEffect } from 'vue';

import { registerAccessDirective } from '@vben/access';
import { registerLoadingDirective } from '@vben/common-ui';
import { preferences } from '@vben/preferences';
import { initStores } from '@vben/stores';
import '@vben/styles';
import '@vben/styles/ele';

import { useTitle } from '@vueuse/core';
import { ElLoading } from 'element-plus';

import { $t, setupI18n } from '#/locales';

import { initComponentAdapter } from './adapter/component';
import { initSetupVbenForm } from './adapter/form';
import { refreshTokenApi } from './api/core/auth';
import App from './app.vue';
import { router } from './router';
import { routes } from './router/routes';
import {
  installSessionAccess,
  reportNavigationFailure,
} from './router/session-access';
import { installAnalytics, useAnalyticsConfig } from './services/analytics';
import { installDictionary } from './services/dictionary/install';
import { installRealtime } from './services/realtime';
import { realtimePorts } from './services/realtime-ports';
import { setupSession } from './services/session/runtime';
import { useAuthStore } from './store';

async function bootstrap(namespace: string) {
  // 统计配置错误时在创建应用前失败
  const analytics = useAnalyticsConfig();

  // 初始化组件适配器
  await initComponentAdapter();

  // 初始化表单组件
  await initSetupVbenForm();

  // // 设置弹窗的默认配置
  // setDefaultModalProps({
  //   fullscreenButton: false,
  // });
  // // 设置抽屉的默认配置
  // setDefaultDrawerProps({
  //   zIndex: 2000,
  // });
  const app = createApp(App);

  // 注册Element Plus提供的v-loading指令
  app.directive('loading', ElLoading.directive);

  // 注册Vben提供的v-loading和v-spinning指令
  registerLoadingDirective(app, {
    loading: false, // Vben提供的v-loading指令和Element Plus提供的v-loading指令二选一即可，此处false表示不注册Vben提供的v-loading指令
    spinning: 'spinning',
  });

  // 国际化 i18n 配置
  await setupI18n(app);

  // 配置 pinia-tore
  await initStores(app, { namespace });
  const session = setupSession({
    namespace,
    refresh: refreshTokenApi,
    expire: () => useAuthStore().expireSession(),
  });
  app.onUnmount(() => session.dispose());
  import.meta.hot?.dispose(() => session.dispose());
  installDictionary(app, session);
  installRealtime({
    app,
    namespace,
    session,
    ports: realtimePorts,
    origin: window.location.origin,
    environment: {
      enabled: import.meta.env.VITE_WEBSOCKET_ENABLED,
      path: import.meta.env.VITE_WEBSOCKET_PATH,
    },
  });
  const releaseAccess = installSessionAccess({
    session,
    router,
    routes,
    clear: () => useAuthStore().clearSessionAccess(),
    onExternalChange: () => {
      void useAuthStore().syncExternalSession().catch(reportNavigationFailure);
    },
  });
  app.onUnmount(releaseAccess);
  import.meta.hot?.dispose(releaseAccess);

  // 安装权限指令
  registerAccessDirective(app);

  // 初始化 tippy
  const { initTippy } = await import('@vben/common-ui/es/tippy');
  initTippy(app);

  // 配置路由及路由守卫
  app.use(router);

  // 配置Motion插件
  const { MotionPlugin } = await import('@vben/plugins/motion');
  app.use(MotionPlugin);

  // 动态更新标题
  watchEffect(() => {
    if (preferences.app.dynamicTitle) {
      const routeTitle = router.currentRoute.value.meta?.title;
      const pageTitle =
        (routeTitle ? `${$t(routeTitle)} - ` : '') + preferences.app.name;
      useTitle(pageTitle);
    }
  });

  app.mount('#app');

  installAnalytics(analytics, document);
}

export { bootstrap };
