<script setup lang="ts">
import type { ProfileApi } from '#/api/core/profile';

import { computed, ref, watch } from 'vue';

import { IconifyIcon } from '@vben/icons';
import { formatDateTime } from '@vben/utils';

import { ElTag } from 'element-plus';

import { updateUserProfile } from '#/api/core/profile';
import { CropperAvatar } from '#/components';
import { createFilePorts } from '#/services/file/ports';

const props = defineProps<{
  profile?: ProfileApi.UserProfileRespVO;
}>();

const emit = defineEmits<{
  success: [];
}>();

const filePorts = createFilePorts({ directory: 'avatar' });

const avatar = ref('');
watch(
  () => props.profile,
  (profile) => {
    avatar.value = profile?.avatar ?? '';
  },
  { immediate: true },
);
const displayName = computed(() => props.profile?.nickname || '-');
const bio = computed(() => props.profile?.bio || '');
const roleNames = computed(() =>
  (props.profile?.roles ?? []).map((role) => role.name).join('、'),
);
const postNames = computed(() =>
  (props.profile?.posts ?? []).map((post) => post.name).join('、'),
);
const tagColors = ['primary', 'success', 'warning', 'danger', 'info'] as const;

async function handleAvatarChange() {
  await updateUserProfile({ avatar: avatar.value || undefined });
  emit('success');
}
</script>

<template>
  <div v-if="profile" class="space-y-5">
    <div class="flex flex-col items-center text-center">
      <CropperAvatar
        v-model:value="avatar"
        :ports="filePorts"
        :show-btn="false"
        :width="112"
        @change="handleAvatarChange"
      />
      <div class="mt-3 text-lg font-medium">{{ displayName }}</div>
      <ElTag class="mt-2" type="primary">{{ profile.username }}</ElTag>
      <p v-if="bio" class="text-muted-foreground mt-3 text-sm leading-6">
        {{ bio }}
      </p>
    </div>

    <div class="space-y-3 border-t pt-4 text-sm">
      <div class="flex items-center gap-3">
        <IconifyIcon icon="lucide:user" class="text-muted-foreground size-4" />
        <span>{{ profile.nickname }}</span>
      </div>
      <div v-if="profile.mobile" class="flex items-center gap-3">
        <IconifyIcon icon="lucide:phone" class="text-muted-foreground size-4" />
        <span>{{ profile.mobile }}</span>
      </div>
      <div v-if="profile.email" class="flex items-center gap-3">
        <IconifyIcon icon="lucide:mail" class="text-muted-foreground size-4" />
        <span>{{ profile.email }}</span>
      </div>
      <div v-if="profile.dept" class="flex items-center gap-3">
        <IconifyIcon
          icon="lucide:building-2"
          class="text-muted-foreground size-4"
        />
        <span>{{ profile.dept.name }}</span>
      </div>
      <div v-if="postNames" class="flex items-center gap-3">
        <IconifyIcon
          icon="lucide:briefcase-business"
          class="text-muted-foreground size-4"
        />
        <span>{{ postNames }}</span>
      </div>
      <div v-if="roleNames" class="flex items-center gap-3">
        <IconifyIcon
          icon="lucide:shield"
          class="text-muted-foreground size-4"
        />
        <span>{{ roleNames }}</span>
      </div>
      <div v-if="profile.address" class="flex items-center gap-3">
        <IconifyIcon
          icon="lucide:map-pin"
          class="text-muted-foreground size-4"
        />
        <span>{{ profile.address }}</span>
      </div>
      <div class="flex items-center gap-3">
        <IconifyIcon icon="lucide:globe" class="text-muted-foreground size-4" />
        <span>{{ profile.loginIp }}</span>
      </div>
      <div class="flex items-center gap-3">
        <IconifyIcon icon="lucide:clock" class="text-muted-foreground size-4" />
        <span>{{ formatDateTime(profile.loginDate) }}</span>
      </div>
    </div>

    <div v-if="profile.tags?.length" class="space-y-2 border-t pt-4">
      <div class="text-muted-foreground text-xs">标签</div>
      <div class="flex flex-wrap gap-2">
        <ElTag
          v-for="(tag, index) in profile.tags"
          :key="tag"
          :type="tagColors[index % tagColors.length]"
        >
          {{ tag }}
        </ElTag>
      </div>
    </div>
  </div>
</template>
