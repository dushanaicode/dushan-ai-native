<script setup lang="ts">
import type { ProfileApi } from '#/api/core/profile';

import { onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import { ElCard, ElTabPane, ElTabs } from 'element-plus';

import { getUserProfile } from '#/api/core/profile';
import { useAuthStore } from '#/store';

import AiPreference from './modules/ai-preference.vue';
import BaseInfo from './modules/base-info.vue';
import OnlineDevices from './modules/online-devices.vue';
import ProfileUser from './modules/profile-user.vue';
import ResetPwd from './modules/reset-pwd.vue';

defineOptions({ name: 'CoreProfile' });

const authStore = useAuthStore();
const activeName = ref('basicInfo');
const loading = ref(false);
const profile = ref<ProfileApi.UserProfileRespVO>();

async function loadProfile() {
  loading.value = true;
  try {
    profile.value = await getUserProfile();
  } finally {
    loading.value = false;
  }
}

async function refreshProfile() {
  await loadProfile();
  await authStore.fetchUserInfo();
}

onMounted(loadProfile);
</script>

<template>
  <Page auto-content-height>
    <div
      v-loading="loading"
      class="grid min-h-0 grid-cols-1 gap-4 lg:grid-cols-[320px_minmax(0,1fr)]"
    >
      <ElCard shadow="never">
        <ProfileUser :profile="profile" @success="refreshProfile" />
      </ElCard>

      <ElCard shadow="never" class="min-w-0">
        <ElTabs v-model="activeName">
          <ElTabPane name="basicInfo" label="基本信息">
            <BaseInfo :profile="profile" @success="refreshProfile" />
          </ElTabPane>
          <ElTabPane name="resetPwd" label="修改密码">
            <ResetPwd />
          </ElTabPane>
          <ElTabPane name="onlineDevices" label="在线设备">
            <OnlineDevices />
          </ElTabPane>
          <ElTabPane name="aiPreference" label="AI 偏好">
            <AiPreference :profile="profile" @success="refreshProfile" />
          </ElTabPane>
        </ElTabs>
      </ElCard>
    </div>
  </Page>
</template>
