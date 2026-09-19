<script lang="ts" setup>
import type { FileBrowserEmits, FileBrowserProps, FileObject } from './typing';

import { computed, onMounted, ref } from 'vue';

import { useAccess } from '@vben/access';
import { IconifyIcon } from '@vben/icons';
import { openWindow } from '@vben/utils';

import { useClipboard } from '@vueuse/core';
import {
  ElButton,
  ElButtonGroup,
  ElDialog,
  ElEmpty,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElSelect,
  ElTooltip,
  ElUpload,
} from 'element-plus';

import FileGridView from './components/file-grid-view.vue';
import FileListView from './components/file-list-view.vue';
import FilePreviewDialog from './components/file-preview-dialog.vue';
import { getPreviewType, getStorageLabel } from './typing';
import { useFileBrowser } from './use-file-browser';

defineOptions({ name: 'FileBrowser' });

withDefaults(defineProps<FileBrowserProps>(), {
  height: '100%',
});

const emit = defineEmits<FileBrowserEmits>();

const {
  breadcrumbs,
  clearSearch,
  configList,
  goUp,
  handleConfigChange,
  handleCreateDirectory,
  handleDeleteBatch,
  handleDeleteItem,
  handleDownloadItem,
  handleRenameItem,
  handleSearch,
  handleUploadFile,
  hasConfig,
  loadConfigList,
  loading,
  navigateTo,
  objects,
  openItem,
  refresh,
  searchKeyword,
  selectedConfigId,
  selectedCount,
  selectedKeys,
  toggleSelect,
  toggleSelectAll,
  viewMode,
} = useFileBrowser();

const { hasAccessByCodes } = useAccess();
const canCreate = computed(() => hasAccessByCodes(['infra:file:create']));
const canDelete = computed(() => hasAccessByCodes(['infra:file:delete']));
const canUpdate = computed(() => hasAccessByCodes(['infra:file:update']));
const canUpload = computed(() => hasAccessByCodes(['infra:file:upload']));

onMounted(() => {
  void loadConfigList();
});

const showCreateFolder = ref(false);
const newFolderName = ref('');

async function confirmCreateFolder() {
  if (!canCreate.value) {
    ElMessage.warning('暂无新建文件夹权限');
    return;
  }

  const folderName = newFolderName.value.trim();
  if (!folderName) {
    ElMessage.warning('请输入文件夹名称');
    return;
  }

  await handleCreateDirectory(folderName);
  ElMessage.success('文件夹创建成功');
  showCreateFolder.value = false;
  newFolderName.value = '';
}

async function handleBeforeUpload(file: File) {
  if (!canUpload.value) {
    ElMessage.warning('暂无文件上传权限');
    return false;
  }

  await handleUploadFile(file);
  ElMessage.success('文件上传成功');
  return false;
}

const showPreview = ref(false);
const previewFile = ref<FileObject | null>(null);

function openPreview(item: FileObject) {
  const previewType = getPreviewType(item.type);
  if (previewType !== 'none' && item.url) {
    previewFile.value = item;
    showPreview.value = true;
  } else if (item.url) {
    openWindow(item.url);
  }
}

async function handleOpen(item: FileObject) {
  if (item.isDirectory) {
    await openItem(item);
    return;
  }

  emit('openFile', item);
  openPreview(item);
}

const { copy } = useClipboard({ legacy: true });

async function handleCopyUrl(item: FileObject) {
  if (!item.url) {
    ElMessage.error('文件 URL 为空');
    return;
  }

  try {
    await copy(item.url);
    ElMessage.success('复制成功');
  } catch {
    ElMessage.error('复制失败');
  }
}

function handleOpenUrl(item: FileObject) {
  openPreview(item);
}

function handleDownload(item: FileObject) {
  handleDownloadItem(item);
}

const showRename = ref(false);
const renameTarget = ref<FileObject | null>(null);
const renameNewName = ref('');

function openRenameDialog(item: FileObject) {
  renameTarget.value = item;
  renameNewName.value = item.name;
  showRename.value = true;
}

async function confirmRename() {
  if (!canUpdate.value) {
    ElMessage.warning('暂无重命名权限');
    return;
  }

  const target = renameTarget.value;
  const newName = renameNewName.value.trim();
  if (!target || !newName) {
    ElMessage.warning('请输入新名称');
    return;
  }

  await handleRenameItem(target.key, newName);
  ElMessage.success('重命名成功');
  showRename.value = false;
  renameTarget.value = null;
  renameNewName.value = '';
}

async function handleDelete(item: FileObject) {
  if (!canDelete.value) {
    ElMessage.warning('暂无删除权限');
    return;
  }

  await ElMessageBox.confirm(`确定要删除「${item.name}」吗？`, '删除确认', {
    cancelButtonText: '取消',
    confirmButtonText: '确定',
    type: 'warning',
  });
  await handleDeleteItem(item.key);
  ElMessage.success('删除成功');
}

async function handleBatchDelete() {
  if (!canDelete.value) {
    ElMessage.warning('暂无删除权限');
    return;
  }

  if (selectedCount.value === 0) {
    return;
  }

  await ElMessageBox.confirm(
    `确定要删除选中的 ${selectedCount.value} 个文件吗？`,
    '批量删除确认',
    {
      cancelButtonText: '取消',
      confirmButtonText: '确定',
      type: 'warning',
    },
  );
  await handleDeleteBatch();
  ElMessage.success('批量删除成功');
}

function handleBreadcrumbClick(prefix: string, index: number) {
  if (index < breadcrumbs.value.length - 1) {
    void navigateTo(prefix);
  }
}

async function handleSearchFiles() {
  await handleSearch(searchKeyword.value);
}
</script>

<template>
  <div class="file-browser" :style="{ height }">
    <div class="file-browser__toolbar">
      <div class="file-browser__toolbar-left">
        <span class="file-browser__label">存储桶</span>
        <ElSelect
          v-model="selectedConfigId"
          placeholder="请选择存储桶"
          size="small"
          class="file-browser__config-select"
          @change="handleConfigChange"
        >
          <ElOption
            v-for="config in configList"
            :key="config.id"
            :label="`${config.name}${config.master ? ' (默认)' : ''}`"
            :value="config.id"
          >
            <div class="file-browser__config-option">
              <span>{{ config.name }}</span>
              <span class="file-browser__config-tag">
                {{ getStorageLabel(config.storage) }}
              </span>
            </div>
          </ElOption>
        </ElSelect>

        <ElInput
          v-model="searchKeyword"
          clearable
          :disabled="!hasConfig"
          placeholder="搜索当前目录"
          size="small"
          class="file-browser__search"
          @clear="clearSearch"
          @keyup.enter="handleSearchFiles"
        >
          <template #append>
            <ElButton :disabled="!hasConfig" @click="handleSearchFiles">
              <IconifyIcon icon="lucide:search" class="size-4" />
            </ElButton>
          </template>
        </ElInput>
      </div>

      <div class="file-browser__toolbar-right">
        <ElUpload
          v-if="canUpload"
          :before-upload="handleBeforeUpload"
          :disabled="!hasConfig"
          multiple
          :show-file-list="false"
        >
          <ElButton :disabled="!hasConfig" size="small" type="primary">
            <IconifyIcon icon="lucide:upload" class="mr-1 size-4" />
            上传文件
          </ElButton>
        </ElUpload>

        <ElButton
          v-if="canCreate"
          :disabled="!hasConfig"
          size="small"
          @click="showCreateFolder = true"
        >
          <IconifyIcon icon="lucide:folder-plus" class="mr-1 size-4" />
          新建文件夹
        </ElButton>

        <ElButton
          v-if="canDelete && selectedCount > 0"
          size="small"
          type="danger"
          @click="handleBatchDelete"
        >
          <IconifyIcon icon="lucide:trash-2" class="mr-1 size-4" />
          删除选中 ({{ selectedCount }})
        </ElButton>

        <ElButtonGroup>
          <ElTooltip content="列表视图" placement="bottom">
            <ElButton
              size="small"
              :type="viewMode === 'list' ? 'primary' : 'default'"
              @click="viewMode = 'list'"
            >
              <IconifyIcon icon="lucide:list" class="size-4" />
            </ElButton>
          </ElTooltip>
          <ElTooltip content="网格视图" placement="bottom">
            <ElButton
              size="small"
              :type="viewMode === 'grid' ? 'primary' : 'default'"
              @click="viewMode = 'grid'"
            >
              <IconifyIcon icon="lucide:grid-2x2" class="size-4" />
            </ElButton>
          </ElTooltip>
        </ElButtonGroup>

        <ElTooltip content="刷新" placement="bottom">
          <ElButton :loading="loading" size="small" @click="refresh">
            <IconifyIcon
              v-if="!loading"
              icon="lucide:refresh-cw"
              class="size-4"
            />
          </ElButton>
        </ElTooltip>
      </div>
    </div>

    <div v-if="hasConfig" class="file-browser__breadcrumb">
      <ElTooltip content="返回上一级" placement="bottom">
        <ElButton
          circle
          :disabled="breadcrumbs.length <= 1 || loading"
          text
          @click="goUp"
        >
          <IconifyIcon icon="lucide:chevron-left" class="size-4" />
        </ElButton>
      </ElTooltip>

      <div class="file-browser__path">
        <span
          v-for="(crumb, index) in breadcrumbs"
          :key="crumb.prefix"
          class="file-browser__path-item"
          :class="{
            'file-browser__path-item--active': index === breadcrumbs.length - 1,
          }"
          @click="handleBreadcrumbClick(crumb.prefix, index)"
        >
          <span>{{ crumb.name }}</span>
          <span
            v-if="index < breadcrumbs.length - 1"
            class="file-browser__path-sep"
          >
            /
          </span>
        </span>
      </div>
    </div>

    <div v-if="!hasConfig" class="file-browser__empty">
      <ElEmpty description="请先选择一个存储配置" />
    </div>

    <div v-else-if="loading" class="file-browser__loading">
      <div class="file-browser__spinner"></div>
      <span>加载中...</span>
    </div>

    <div v-else-if="objects.length === 0" class="file-browser__empty">
      <ElEmpty description="当前目录为空" />
    </div>

    <template v-else>
      <FileListView
        v-if="viewMode === 'list'"
        :can-delete="canDelete"
        :can-update="canUpdate"
        :objects="objects"
        :selected-keys="selectedKeys"
        @copy-url="handleCopyUrl"
        @delete="handleDelete"
        @download="handleDownload"
        @open="handleOpen"
        @open-url="handleOpenUrl"
        @rename="openRenameDialog"
        @toggle-select="toggleSelect"
        @toggle-select-all="toggleSelectAll"
      />
      <FileGridView
        v-else
        :can-delete="canDelete"
        :can-update="canUpdate"
        :objects="objects"
        :selected-keys="selectedKeys"
        @copy-url="handleCopyUrl"
        @delete="handleDelete"
        @download="handleDownload"
        @open="handleOpen"
        @open-url="handleOpenUrl"
        @rename="openRenameDialog"
        @toggle-select="toggleSelect"
      />
    </template>

    <ElDialog
      v-model="showCreateFolder"
      append-to-body
      title="新建文件夹"
      width="400px"
    >
      <ElInput
        v-model="newFolderName"
        placeholder="请输入文件夹名称"
        @keyup.enter="confirmCreateFolder"
      />
      <template #footer>
        <ElButton @click="showCreateFolder = false">取消</ElButton>
        <ElButton type="primary" @click="confirmCreateFolder">确定</ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="showRename" append-to-body title="重命名" width="400px">
      <ElInput
        v-model="renameNewName"
        placeholder="请输入新名称"
        @keyup.enter="confirmRename"
      />
      <template #footer>
        <ElButton @click="showRename = false">取消</ElButton>
        <ElButton type="primary" @click="confirmRename">确定</ElButton>
      </template>
    </ElDialog>

    <FilePreviewDialog v-model="showPreview" :file="previewFile" />
  </div>
</template>

<style src="./styles/file-browser.css"></style>
