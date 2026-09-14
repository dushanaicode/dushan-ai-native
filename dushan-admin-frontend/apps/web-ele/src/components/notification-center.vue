<script setup lang="ts">
import type { NotificationRuntime } from '../services/notifications/runtime';

import { computed, ref, watch } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { Bell } from '@vben/icons';
import { $t } from '@vben/locales';

import {
  ElAlert,
  ElBadge,
  ElButton,
  ElEmpty,
  ElPopover,
  ElScrollbar,
} from 'element-plus';

import NotificationContent from './notification-content.vue';

const props = defineProps<{ runtime: NotificationRuntime }>();
const visible = ref(false);
const selectedId = ref<string>();
const failure = ref(false);
const selected = computed(() =>
  props.runtime.notifications.find((item) => item.id === selectedId.value),
);
const [Modal, modal] = useVbenModal({ footer: false });
watch(selected, (item) => {
  if (!item) modal.close();
});
async function run(action: () => Promise<void>) {
  failure.value = false;
  try {
    await action();
  } catch (error) {
    if (!(error instanceof DOMException && error.name === 'AbortError'))
      failure.value = true;
  }
}
function open(id: string) {
  selectedId.value = id;
  visible.value = false;
  modal.open();
  void run(() => props.runtime.markRead(id));
}
</script>

<template>
  <ElPopover
    v-model:visible="visible"
    trigger="click"
    :width="360"
    @show="run(() => runtime.ensure())"
  >
    <template #reference>
      <ElButton text circle :aria-label="$t('utils.notification.title')">
        <ElBadge
          :value="runtime.unreadCount"
          :hidden="runtime.unreadCount === 0"
          :max="99"
        >
          <Bell class="size-5" />
        </ElBadge>
      </ElButton>
    </template>
    <div class="flex items-center justify-between">
      <strong>{{ $t('utils.notification.title') }}</strong>
      <ElButton
        text
        :disabled="runtime.unreadCount === 0"
        @click="run(() => runtime.markAllRead())"
      >
        <span>{{ $t('utils.notification.readAll') }}</span>
      </ElButton>
    </div>
    <ElAlert
      v-if="failure || runtime.error"
      type="error"
      :title="$t('utils.notification.failed')"
      :closable="false"
    />
    <ElScrollbar max-height="400px" :aria-busy="runtime.loading">
      <ElEmpty
        v-if="runtime.notifications.length === 0"
        :description="$t('utils.notification.empty')"
        :image-size="48"
      />
      <button
        v-for="item in runtime.notifications"
        :key="item.id"
        type="button"
        class="hover:bg-accent flex w-full flex-col gap-1 border-b p-3 text-left"
        @click="open(item.id)"
      >
        <span :class="{ 'font-semibold': !item.isRead }">{{ item.title }}</span>
        <time class="text-muted-foreground text-xs">{{ item.createTime }}</time>
      </button>
    </ElScrollbar>
    <ElButton
      text
      :loading="runtime.loading"
      @click="run(() => runtime.refresh())"
    >
      <span>{{ $t('utils.notification.refresh') }}</span>
    </ElButton>
  </ElPopover>
  <Modal :title="selected?.title">
    <ElAlert
      v-if="failure"
      type="error"
      :title="$t('utils.notification.failed')"
      :closable="false"
    />
    <template v-if="selected">
      <time>{{ selected.createTime }}</time>
      <NotificationContent :content="selected.content" />
      <ElButton
        v-if="!selected.isRead"
        text
        @click="run(() => runtime.markRead(selected!.id))"
      >
        <span>{{ $t('utils.notification.read') }}</span>
      </ElButton>
    </template>
  </Modal>
</template>
