<script lang="ts" setup>
import type { FileObject } from '../typing';

import { computed } from 'vue';

import { IconifyIcon } from '@vben/icons';
import { $t } from '@vben/locales';

import {
  ElButton,
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElTooltip,
} from 'element-plus';

import { getFileIcon } from '../typing';

defineOptions({ name: 'FileListView' });

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
  toggleSelectAll: [];
}>();

const allSelected = computed(
  () =>
    props.objects.length > 0 &&
    props.selectedKeys.length === props.objects.length,
);

function handleCommand(command: string, item: FileObject) {
  switch (command) {
    case 'delete': {
      emit('delete', item);
      break;
    }
    case 'download': {
      emit('download', item);
      break;
    }
    case 'rename': {
      emit('rename', item);
      break;
    }
  }
}

function formatSize(size?: null | number) {
  if (size === undefined || size === null) {
    return '-';
  }

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let value = size;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index++;
  }
  return `${value.toFixed(index > 0 ? 2 : 0)} ${units[index]}`;
}

function formatDate(value?: null | string) {
  if (!value) {
    return '-';
  }

  try {
    return new Date(value).toLocaleString('zh-CN');
  } catch {
    return value;
  }
}
</script>

<template>
  <div class="file-list">
    <div class="file-list__header">
      <div class="file-list__cell file-list__cell--checkbox">
        <input
          type="checkbox"
          :aria-label="$t('utils.fileBrowser.selectAll')"
          :checked="allSelected"
          :indeterminate="selectedKeys.length > 0 && !allSelected"
          @change="emit('toggleSelectAll')"
        />
      </div>
      <div class="file-list__cell file-list__cell--icon"></div>
      <div class="file-list__cell file-list__cell--name">
        {{ $t('utils.fileBrowser.name') }}
      </div>
      <div class="file-list__cell file-list__cell--size">
        {{ $t('utils.fileBrowser.size') }}
      </div>
      <div class="file-list__cell file-list__cell--time">
        {{ $t('utils.fileBrowser.modified') }}
      </div>
      <div class="file-list__cell file-list__cell--type">
        {{ $t('utils.fileBrowser.type') }}
      </div>
      <div class="file-list__cell file-list__cell--actions">
        {{ $t('utils.fileBrowser.actions') }}
      </div>
    </div>

    <div
      v-for="item in objects"
      :key="item.key"
      class="file-list__row"
      :class="{ 'file-list__row--selected': selectedKeys.includes(item.key) }"
      @dblclick="emit('open', item)"
    >
      <div class="file-list__cell file-list__cell--checkbox">
        <input
          type="checkbox"
          :aria-label="$t('utils.fileBrowser.selectFile', { name: item.name })"
          :checked="selectedKeys.includes(item.key)"
          @change.stop="emit('toggleSelect', item.key)"
        />
      </div>
      <div class="file-list__cell file-list__cell--icon">
        <IconifyIcon :icon="getFileIcon(item)" class="file-list__icon" />
      </div>
      <div class="file-list__cell file-list__cell--name">
        <button
          class="file-list__name-button"
          :class="{ 'file-list__name-button--dir': item.isDirectory }"
          type="button"
          @click="emit('open', item)"
        >
          {{ item.name }}
        </button>
      </div>
      <div class="file-list__cell file-list__cell--size">
        {{ item.isDirectory ? '-' : formatSize(item.size) }}
      </div>
      <div class="file-list__cell file-list__cell--time">
        {{ formatDate(item.lastModified) }}
      </div>
      <div class="file-list__cell file-list__cell--type">
        {{
          item.isDirectory ? $t('utils.fileBrowser.folder') : item.type || '-'
        }}
      </div>
      <div class="file-list__cell file-list__cell--actions">
        <template v-if="!item.isDirectory">
          <ElTooltip :content="$t('utils.fileBrowser.copy')" placement="top">
            <ElButton link type="primary" @click.stop="emit('copyUrl', item)">
              <IconifyIcon icon="lucide:copy" class="size-4" />
            </ElButton>
          </ElTooltip>
          <ElTooltip :content="$t('utils.fileBrowser.preview')" placement="top">
            <ElButton link type="primary" @click.stop="emit('openUrl', item)">
              <IconifyIcon icon="lucide:external-link" class="size-4" />
            </ElButton>
          </ElTooltip>
        </template>
        <ElTooltip
          v-else
          :content="$t('utils.fileBrowser.openFolder')"
          placement="top"
        >
          <ElButton link type="primary" @click.stop="emit('open', item)">
            <IconifyIcon icon="lucide:folder-open" class="size-4" />
          </ElButton>
        </ElTooltip>

        <div class="file-list__more" @click.stop>
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
                <ElDropdownItem v-if="!item.isDirectory" command="download">
                  {{ $t('utils.fileBrowser.download') }}
                </ElDropdownItem>
                <ElDropdownItem v-if="props.canUpdate" command="rename">
                  {{ $t('utils.fileBrowser.rename') }}
                </ElDropdownItem>
                <ElDropdownItem v-if="props.canDelete" command="delete" divided>
                  <span class="file-browser__danger">{{
                    $t('common.delete')
                  }}</span>
                </ElDropdownItem>
              </ElDropdownMenu>
            </template>
          </ElDropdown>
        </div>
      </div>
    </div>
  </div>
</template>
