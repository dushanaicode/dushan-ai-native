import type { Recordable, UserInfo } from '@vben/types';

import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { LOGIN_PATH } from '@vben/constants';
import { preferences } from '@vben/preferences';
import { useAccessStore, useTabbarStore, useUserStore } from '@vben/stores';

import { ElNotification } from 'element-plus';
import { defineStore } from 'pinia';

import { getAccessCodesApi, getUserInfoApi, loginApi, logoutApi } from '#/api';
import { $t } from '#/locales';

import { getSession } from '../services/session/runtime';

export const useAuthStore = defineStore('auth', () => {
  const accessStore = useAccessStore();
  const userStore = useUserStore();
  const tabbarStore = useTabbarStore();
  const router = useRouter();
  const loginLoading = ref(false);
  let loginPromise: Promise<{ userInfo: UserInfo }> | undefined;
  let logoutPromise: Promise<void> | undefined;

  function clearSessionAccess() {
    tabbarStore.$reset();
    tabbarStore.renderRouteView = false;
    userStore.$reset();
    accessStore.$patch({
      accessCodes: [],
      accessMenus: [],
      accessRoutes: [],
      isAccessChecked: false,
      isLockScreen: false,
      lockScreenPassword: undefined,
      refreshToken: null,
    });
  }

  function authLogin(
    params: Recordable<any>,
    onSuccess?: () => Promise<void> | void,
  ) {
    loginPromise ??= runLogin(params, onSuccess).finally(() => {
      loginPromise = undefined;
    });
    return loginPromise;
  }

  async function runLogin(
    params: Recordable<any>,
    onSuccess?: () => Promise<void> | void,
  ) {
    const session = getSession();
    const wasExpired = accessStore.loginExpired;
    session.replace(null);
    let scope = session.capture();
    loginLoading.value = true;
    try {
      const { accessToken } = await loginApi(params);
      session.assertCurrent(scope);
      session.replace(accessToken);
      scope = session.capture();
      const [userInfo, accessCodes] = await Promise.all([
        fetchUserInfo(),
        getAccessCodesApi(),
      ]);
      session.assertCurrent(scope);
      accessStore.setAccessCodes(accessCodes);
      accessStore.setLoginExpired(false);
      if (wasExpired) {
        // URL 保持不变，但权限树已经撤销，需要重新判定当前页面是否可达。
        await router.replace(router.currentRoute.value.fullPath);
      } else {
        await (onSuccess ? onSuccess() : router.push(userInfo.homePath));
      }
      session.assertCurrent(scope);
      if (!wasExpired && userInfo.realName)
        ElNotification({
          message: `${$t('authentication.loginSuccessDesc')}:${userInfo.realName}`,
          title: $t('authentication.loginSuccess'),
          type: 'success',
        });
      return { userInfo };
    } catch (error) {
      if (session.capture().generation === scope.generation)
        session.replace(null);
      throw error;
    } finally {
      loginLoading.value = false;
    }
  }

  function logout(redirect = true) {
    if (logoutPromise) return logoutPromise;
    const session = getSession();
    const authenticated = session.capture().token !== null;
    session.replace(null);
    const scope = session.capture();
    logoutPromise = (async () => {
      try {
        if (authenticated) await logoutApi();
      } finally {
        if (session.capture().generation === scope.generation) {
          accessStore.setLoginExpired(false);
          await redirectToLogin(redirect);
        }
      }
    })().finally(() => {
      logoutPromise = undefined;
    });
    return logoutPromise;
  }

  async function redirectToLogin(redirect = true) {
    await router.replace({
      path: LOGIN_PATH,
      query: redirect
        ? { redirect: encodeURIComponent(router.currentRoute.value.fullPath) }
        : {},
    });
  }

  async function expireSession() {
    const modal =
      preferences.app.loginExpiredMode === 'modal' &&
      router.currentRoute.value.matched.some((route) => route.name === 'Root');
    accessStore.setLoginExpired(modal);
    if (!modal) await redirectToLogin();
  }

  async function syncExternalSession() {
    accessStore.setLoginExpired(false);
    await (getSession().capture().token === null
      ? redirectToLogin()
      : router.replace(router.currentRoute.value.fullPath));
  }

  async function refreshAccess() {
    const session = getSession();
    session.replace(session.capture().token);
    await router.replace(router.currentRoute.value.fullPath);
  }

  async function fetchUserInfo() {
    const scope = getSession().capture();
    const userInfo = await getUserInfoApi();
    getSession().assertCurrent(scope);
    userStore.setUserInfo(userInfo);
    return userInfo;
  }

  function $reset() {
    loginLoading.value = false;
  }

  return {
    $reset,
    authLogin,
    clearSessionAccess,
    expireSession,
    fetchUserInfo,
    loginLoading,
    logout,
    refreshAccess,
    syncExternalSession,
  };
});
