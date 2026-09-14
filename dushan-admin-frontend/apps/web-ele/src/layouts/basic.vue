<script lang="ts" setup>
import { computed, watch } from 'vue';
import { useRouter } from 'vue-router';

import { AuthenticationLoginExpiredModal } from '@vben/common-ui';
import { useWatermark } from '@vben/hooks';
import { BookOpenText, CircleHelp, SvgGithubIcon } from '@vben/icons';
import { BasicLayout, LockScreen, UserDropdown } from '@vben/layouts';
import { preferences, usePreferences } from '@vben/preferences';
import { useAccessStore, useUserStore } from '@vben/stores';
import { openWindow } from '@vben/utils';

import { $t } from '#/locales';
import {
  buildDocUrl,
  projectLinks,
  useDocLinkConfig,
} from '#/services/doc-links';
import { useAuthStore } from '#/store';
import LoginForm from '#/views/_core/authentication/login.vue';

import NotificationCenter from '../components/notification-center.vue';
import { useRealtime } from '../services/realtime';

const realtime = useRealtime();

const router = useRouter();
const userStore = useUserStore();
const authStore = useAuthStore();
const accessStore = useAccessStore();
const { destroyWatermark, updateWatermark } = useWatermark();
const { isDark } = usePreferences();

const { docSite, deepDiveSite } = useDocLinkConfig();

function openLink(url: string) {
  openWindow(url, { target: '_blank' });
}

const menus = computed(() => [
  {
    handler: () => {
      router.push({ name: 'Profile' });
    },
    icon: 'lucide:user',
    text: $t('page.auth.profile'),
  },
  ...(docSite
    ? [
        {
          handler: () =>
            openLink(
              buildDocUrl(docSite, '', {
                channel: 'help_menu',
                content: 'home',
              }),
            ),
          icon: BookOpenText,
          text: $t('utils.docLinks.docs'),
        },
      ]
    : []),
  ...(deepDiveSite
    ? [
        {
          handler: () =>
            openLink(
              buildDocUrl(deepDiveSite, '', {
                channel: 'help_menu',
                content: 'home',
              }),
            ),
          icon: 'lucide:graduation-cap',
          text: $t('utils.docLinks.deepDive'),
        },
      ]
    : []),
  {
    handler: () => openLink(projectLinks.github),
    icon: SvgGithubIcon,
    text: 'GitHub',
  },
  {
    handler: () => openLink(projectLinks.mirror),
    icon: 'simple-icons:gitee',
    text: 'Gitee',
  },
  {
    handler: () => openLink(projectLinks.issues),
    icon: CircleHelp,
    text: $t('utils.docLinks.feedback'),
  },
]);

const avatar = computed(() => {
  return userStore.userInfo?.avatar ?? preferences.app.defaultAvatar;
});

async function handleLogout() {
  await authStore.logout(false);
}

watch(
  () => ({
    enable: preferences.app.watermark,
    content: preferences.app.watermarkContent,
    isDark: isDark.value,
  }),
  async ({ enable, content, isDark: isDarkValue }) => {
    if (enable) {
      const watermarkColor = isDarkValue
        ? 'rgba(255, 255, 255, 0.12)'
        : 'rgba(0, 0, 0, 0.12)';

      await updateWatermark({
        advancedStyle: {
          colorStops: [
            {
              color: watermarkColor,
              offset: 0,
            },
            {
              color: watermarkColor,
              offset: 1,
            },
          ],
          type: 'linear',
        },
        content:
          content ||
          `${userStore.userInfo?.username} - ${userStore.userInfo?.realName}`,
      });
    } else {
      destroyWatermark();
    }
  },
  {
    immediate: true,
  },
);
</script>

<template>
  <BasicLayout
    :avatar
    :text="userStore.userInfo?.realName"
    @clear-preferences-and-logout="handleLogout"
    @logout="handleLogout"
  >
    <template #user-dropdown>
      <UserDropdown
        :avatar
        :menus
        :text="userStore.userInfo?.realName"
        @clear-preferences-and-logout="handleLogout"
        @logout="handleLogout"
      />
    </template>
    <template #notification>
      <NotificationCenter v-if="realtime" :runtime="realtime.notifications" />
    </template>
    <template #extra>
      <AuthenticationLoginExpiredModal
        v-model:open="accessStore.loginExpired"
        :avatar
      >
        <LoginForm />
      </AuthenticationLoginExpiredModal>
    </template>
    <template #lock-screen>
      <LockScreen :avatar @to-login="handleLogout" />
    </template>
  </BasicLayout>
</template>
