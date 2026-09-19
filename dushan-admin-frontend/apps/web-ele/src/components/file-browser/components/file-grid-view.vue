<script lang="ts" setup>
import type { FileObject } from '../typing';

import { IconifyIcon } from '@vben/icons';

import { ElDropdown, ElDropdownItem, ElDropdownMenu } from 'element-plus';

import { getFileIcon, isImageType } from '../typing';

defineOptions({ name: 'FileGridView' });

defineProps<{
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
        :checked="selectedKeys.includes(item.key)"
        @change.stop="emit('toggleSelect', item.key)"
        @click.stop
      />

      <div class="file-grid__more" @click.stop>
        <ElDropdown
          trigger="click"
          @command="(command) => handleCommand(String(command), item)"
        >
          <span class="more-trigger" title="更多操作">
            <IconifyIcon icon="lucide:more-horizontal" class="size-4" />
          </span>
          <template #dropdown>
            <ElDropdownMenu>
              <ElDropdownItem command="open">
                {{ item.isDirectory ? '打开' : '预览' }}
              </ElDropdownItem>
              <ElDropdownItem v-if="!item.isDirectory" command="copy">
                复制链接
              </ElDropdownItem>
              <ElDropdownItem v-if="!item.isDirectory" command="download">
                下载
              </ElDropdownItem>
              <ElDropdownItem v-if="canUpdate" command="rename">
                重命名
              </ElDropdownItem>
              <ElDropdownItem v-if="canDelete" command="delete" divided>
                <span class="file-browser__danger">删除</span>
              </ElDropdownItem>
            </ElDropdownMenu>
          </template>
        </ElDropdown>
      </div>

      <div class="file-grid__preview" @click="emit('open', item)">
        <img
          v-if="isImageType(item.type) && item.url"
          :alt="item.name"
          class="file-grid__thumb"
          loading="lazy"
          :src="item.url"
          @error="onImageError"
        />
        <IconifyIcon v-else :icon="getFileIcon(item)" class="file-grid__icon" />
      </div>
      <div class="file-grid__name" :title="item.name">{{ item.name }}</div>
    </div>
  </div>
</template>
