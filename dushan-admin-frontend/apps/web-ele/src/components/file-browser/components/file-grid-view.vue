<script lang="ts" setup>
import type { FileObject } from '../typing';

import { ref, watch } from 'vue';

import { IconifyIcon } from '@vben/icons';
import { $t } from '@vben/locales';

import { ElDropdown, ElDropdownItem, ElDropdownMenu } from 'element-plus';

import { notifyError } from '#/api/error-feedback';
import { resolveFileUrl } from '#/services/file/file-access';

import { getFileIcon, isImageType } from '../typing';

defineOptions({ name: 'FileGridView' });

const props = defineProps<{
  canDelete?: boolean;
  canUpdate?: boolean;
  objects: FileObject[];
  selectedKeys: string[];
}>();

const emit = defineEmits<{
  copyUrl: [item: FileObject];
  delete: [item: FileObject];
  download: [item: FileObject];
  open: [item: FileObject];
  openUrl: [item: FileObject];
  rename: [item: FileObject];
  toggleSelect: [key: string];
}>();
const thumbnailUrls = ref(new Map<string, string>());
watch(
  () => props.objects,
  (objects, _, onCleanup) => {
    const controller = new AbortController();
    onCleanup(() => controller.abort());
    thumbnailUrls.value = new Map();
    for (const item of objects) {
      if (!item.url || !isImageType(item.type)) continue;
      void resolveFileUrl(item.url, controller.signal)
        .then((url) => {
          if (!controller.signal.aborted)
            thumbnailUrls.value.set(item.key, url);
        })
        .catch((error: unknown) => {
          if (!controller.signal.aborted) notifyError(error);
        });
    }
  },
  { immediate: true },
);

function handleCommand(command: string, item: FileObject) {
  switch (command) {
    case 'copy': {
      emit('copyUrl', item);
      break;
    }
    case 'delete': {
      emit('delete', item);
      break;
    }
    case 'download': {
      emit('download', item);
      break;
    }
    case 'open': {
      if (item.isDirectory) {
        emit('open', item);
      } else {
        emit('openUrl', item);
      }
      break;
    }
    case 'rename': {
      emit('rename', item);
      break;
    }
  }
}

function onImageError(event: Event) {
  const target = event.target as HTMLImageElement | null;
  if (target) {
    target.style.display = 'none';
  }
}
</script>

<template>
  <div class="file-grid">
    <div
      v-for="item in objects"
      :key="item.key"
      class="file-grid__item"
      :class="{ 'file-grid__item--selected': selectedKeys.includes(item.key) }"
      @dblclick="emit('open', item)"
    >
      <input
        class="file-grid__checkbox"
        type="checkbox"
        :aria-label="$t('utils.fileBrowser.selectFile', { name: item.name })"
        :checked="selectedKeys.includes(item.key)"
        @change.stop="emit('toggleSelect', item.key)"
        @click.stop
      />

      <div class="file-grid__more" @click.stop>
        <ElDropdown
          trigger="click"
          @command="(command) => handleCommand(String(command), item)"
        >
          <button
            type="button"
            class="more-trigger"
            :aria-label="$t('utils.fileBrowser.more')"
          >
            <IconifyIcon icon="lucide:more-horizontal" class="size-4" />
          </button>
          <template #dropdown>
            <ElDropdownMenu>
              <ElDropdownItem command="open">
                {{
                  item.isDirectory
                    ? $t('utils.fileBrowser.open')
                    : $t('utils.fileBrowser.preview')
                }}
              </ElDropdownItem>
              <ElDropdownItem v-if="!item.isDirectory" command="copy">
                {{ $t('utils.fileBrowser.copy') }}
              </ElDropdownItem>
              <ElDropdownItem v-if="!item.isDirectory" command="download">
                {{ $t('utils.fileBrowser.download') }}
              </ElDropdownItem>
              <ElDropdownItem v-if="canUpdate" command="rename">
                {{ $t('utils.fileBrowser.rename') }}
              </ElDropdownItem>
              <ElDropdownItem v-if="canDelete" command="delete" divided>
                <span class="file-browser__danger">{{
                  $t('common.delete')
                }}</span>
              </ElDropdownItem>
            </ElDropdownMenu>
          </template>
        </ElDropdown>
      </div>

      <div class="file-grid__preview" @click="emit('open', item)">
        <img
          v-if="thumbnailUrls.has(item.key)"
          :alt="item.name"
          class="file-grid__thumb"
          loading="lazy"
          :src="thumbnailUrls.get(item.key)"
          @error="onImageError"
        />
        <IconifyIcon v-else :icon="getFileIcon(item)" class="file-grid__icon" />
      </div>
      <div class="file-grid__name" :title="item.name">{{ item.name }}</div>
    </div>
  </div>
</template>
