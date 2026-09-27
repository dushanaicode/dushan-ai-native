import type { UserInfo } from '@vben/types';

import type { MenuNode } from '../router/menu-adapter';

import type { AuthApi } from '#/api/core/auth';

import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { LOGIN_PATH } from '@vben/constants';
import { preferences } from '@vben/preferences';
import { useAccessStore, useTabbarStore, useUserStore } from '@vben/stores';

import { ElNotification } from 'element-plus';
import { defineStore } from 'pinia';

import {
  getPermissionInfoApi,
  loginApi,
  logoutApi,
  registerApi,
  smsLoginApi,
  socialLoginApi,
} from '#/api';
import { consumeQrLogin } from '#/api/core/qr-login';
import { $t } from '#/locales';

import { getSession } from '../services/session/runtime';
import { useTenantStore } from './tenant';

export const useAuthStore = defineStore('auth', () => {
  const accessStore = useAccessStore();
  const tenantStore = useTenantStore();
  const userStore = useUserStore();
  const tabbarStore = useTabbarStore();
  const router = useRouter();
  const loginLoading = ref(false);
  // 后端把菜单与身份放在同一响应；守卫在 userInfo 已存在时会跳过 fetchUserInfo，
  // 因此菜单在此按代次持有，由 clearSessionAccess 一并清除。
  const accessMenus = ref<MenuNode[] | undefined>();
  let loginPromise: Promise<{ userInfo: UserInfo }> | undefined;
  let logoutPromise: Promise<void> | undefined;

  function clearSessionAccess() {
    tenantStore.currentTenantId = null;
    accessMenus.value = undefined;
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
    params: AuthApi.LoginParams,
    tenantId?: string,
    onSuccess?: () => Promise<void> | void,
  ) {
    return startLogin(() => loginApi(params, tenantId), onSuccess);
  }

  function authSmsLogin(params: AuthApi.SmsLoginParams, tenantId?: string) {
    return startLogin(() => smsLoginApi(params, tenantId));
  }

  function authQrLogin(ticket: string) {
    return startLogin(() => consumeQrLogin(ticket));
  }

  function authRegister(params: AuthApi.RegisterParams, tenantId?: string) {
    return startLogin(() => registerApi(params, tenantId));
  }

  function authSocialLogin(
    params: AuthApi.SocialLoginParams,
    onSuccess?: () => Promise<void> | void,
  ) {
    return startLogin(() => socialLoginApi(params), onSuccess);
  }

  function startLogin(
    login: () => Promise<AuthApi.LoginResult>,
    onSuccess?: () => Promise<void> | void,
  ) {
    loginPromise ??= runLogin(login, onSuccess).finally(() => {
      loginPromise = undefined;
    });
    return loginPromise;
  }

  async function runLogin(
    login: () => Promise<AuthApi.LoginResult>,
    onSuccess?: () => Promise<void> | void,
  ) {
    const session = getSession();
    const wasExpired = accessStore.loginExpired;
    session.replace(null);
    let scope = session.capture();
    loginLoading.value = true;
    try {
      const { accessToken, tenantId } = await login();
      session.assertCurrent(scope);
      session.replace(accessToken);
      tenantStore.currentTenantId = tenantId;
      scope = session.capture();
      const userInfo = await fetchUserInfo();
      session.assertCurrent(scope);
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
    // 先取令牌再清本地：后端只在请求带 Authorization 时撤销服务端会话族。
    const token = session.capture().token;
    session.replace(null);
    const scope = session.capture();
    logoutPromise = (async () => {
      try {
        if (token !== null) await logoutApi(token);
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
    const info = await getPermissionInfoApi();
    getSession().assertCurrent(scope);
    tenantStore.currentTenantId = info.tenantId;
    accessMenus.value = info.menus;
    accessStore.setAccessCodes(info.permissions);
    userStore.setUserInfo(info.user);
    return info.user;
  }

  /** 供 generateAccess 取用本代次的授权菜单；缺失说明装配顺序被破坏，直接失败。 */
  function requireAccessMenus() {
    if (accessMenus.value === undefined)
      throw new Error('尚未获取授权菜单，无法生成路由');
    return accessMenus.value;
  }

  function $reset() {
    loginLoading.value = false;
  }

  return {
    $reset,
    authLogin,
    authQrLogin,
    authRegister,
    authSocialLogin,
    authSmsLogin,
    clearSessionAccess,
    expireSession,
    fetchUserInfo,
    loginLoading,
    logout,
    refreshAccess,
    requireAccessMenus,
    syncExternalSession,
  };
});
