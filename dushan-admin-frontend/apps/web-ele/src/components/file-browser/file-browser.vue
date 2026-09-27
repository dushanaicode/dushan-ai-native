<script lang="ts" setup>
import type { FileBrowserEmits, FileBrowserProps, FileObject } from './typing';

import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { useAccess } from '@vben/access';
import { Loading } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';
import { $t } from '@vben/locales';
import { openWindow } from '@vben/utils';

import { useClipboard } from '@vueuse/core';
import {
  ElAlert,
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

import { notifyError } from '#/api/error-feedback';

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
const router = useRouter();

const {
  breadcrumbs,
  clearSearch,
  configList,
  errorMessage,
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
  loadFailed,
  loading,
  navigateTo,
  objects,
  openItem,
  refresh,
  searchKeyword,
  selectedConfigId,
  selectedConfig,
  selectedCount,
  selectedKeys,
  sortBy,
  sortedObjects,
  toggleSelect,
  toggleSelectAll,
  uploading,
  viewMode,
} = useFileBrowser();

const { hasAccessByCodes } = useAccess();
const canCreate = computed(() => hasAccessByCodes(['infra:file:create']));
const canDelete = computed(() => hasAccessByCodes(['infra:file:delete']));
const canUpdate = computed(() => hasAccessByCodes(['infra:file:update']));
const canUpload = computed(() => hasAccessByCodes(['infra:file:upload']));
const canManageStorage = computed(() =>
  hasAccessByCodes(['infra:file:config:query']),
);
const mutationLoading = ref(false);

async function mutate(operation: () => Promise<void>) {
  if (mutationLoading.value) return;
  mutationLoading.value = true;
  try {
    await operation();
  } catch (error) {
    notifyError(error);
  } finally {
    mutationLoading.value = false;
  }
}

function validName(name: string) {
  return name !== '.' && name !== '..' && !/[\\/:]/.test(name);
}

onMounted(() => {
  void loadConfigList();
});

const showCreateFolder = ref(false);
const newFolderName = ref('');

async function confirmCreateFolder() {
  if (!canCreate.value) {
    ElMessage.warning($t('utils.fileBrowser.noPermission'));
    return;
  }

  const folderName = newFolderName.value.trim();
  if (!folderName) {
    ElMessage.warning($t('utils.fileBrowser.folderName'));
    return;
  }

  if (!validName(folderName)) {
    ElMessage.warning($t('utils.fileBrowser.invalidName'));
    return;
  }
  await mutate(async () => {
    await handleCreateDirectory(folderName);
    ElMessage.success($t('utils.fileBrowser.createSuccess'));
    showCreateFolder.value = false;
    newFolderName.value = '';
  });
}

async function handleBeforeUpload(file: File) {
  if (!canUpload.value) {
    ElMessage.warning($t('utils.fileBrowser.noPermission'));
    return false;
  }

  try {
    await handleUploadFile(file);
    ElMessage.success($t('utils.fileBrowser.uploadSuccess'));
  } catch (error) {
    notifyError(error);
  }
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
    ElMessage.error($t('utils.fileBrowser.missingUrl'));
    return;
  }

  try {
    await copy(item.url);
    ElMessage.success($t('utils.fileBrowser.copySuccess'));
  } catch {
    ElMessage.error($t('utils.fileBrowser.copyFailed'));
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
    ElMessage.warning($t('utils.fileBrowser.noPermission'));
    return;
  }

  const target = renameTarget.value;
  const newName = renameNewName.value.trim();
  if (!target || !newName) {
    ElMessage.warning($t('utils.fileBrowser.newName'));
    return;
  }
  if (newName === target.name) {
    showRename.value = false;
    return;
  }

  if (!validName(newName)) {
    ElMessage.warning($t('utils.fileBrowser.invalidName'));
    return;
  }
  await mutate(async () => {
    await handleRenameItem(target.key, newName);
    ElMessage.success($t('utils.fileBrowser.renameSuccess'));
    showRename.value = false;
    renameTarget.value = null;
    renameNewName.value = '';
  });
}

async function handleDelete(item: FileObject) {
  if (!canDelete.value) {
    ElMessage.warning($t('utils.fileBrowser.noPermission'));
    return;
  }

  await mutate(async () => {
    await ElMessageBox.confirm(
      $t('utils.fileBrowser.deleteConfirm', { name: item.name }),
      $t('utils.fileBrowser.confirmDelete'),
      {
        cancelButtonText: $t('utils.fileBrowser.cancel'),
        confirmButtonText: $t('utils.fileBrowser.confirm'),
        type: 'warning',
      },
    );
    await handleDeleteItem(item.key);
    ElMessage.success($t('utils.fileBrowser.deleteSuccess'));
  });
}

async function handleBatchDelete() {
  if (!canDelete.value) {
    ElMessage.warning($t('utils.fileBrowser.noPermission'));
    return;
  }

  if (selectedCount.value === 0) {
    return;
  }

  await mutate(async () => {
    await ElMessageBox.confirm(
      $t('utils.fileBrowser.batchConfirm', { count: selectedCount.value }),
      $t('utils.fileBrowser.confirmDelete'),
      {
        cancelButtonText: $t('utils.fileBrowser.cancel'),
        confirmButtonText: $t('utils.fileBrowser.confirm'),
        type: 'warning',
      },
    );
    await handleDeleteBatch();
    ElMessage.success($t('utils.fileBrowser.deleteSuccess'));
  });
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
    <div class="file-browser__heading">
      <div>
        <h2>
          <IconifyIcon icon="lucide:folder-open" class="size-5" />{{
            $t('utils.fileBrowser.title')
          }}
        </h2>
        <p>{{ $t('utils.fileBrowser.subtitle') }}</p>
      </div>
      <ElButton
        v-if="canManageStorage"
        link
        type="primary"
        @click="router.push('/infra/file/config')"
      >
        <IconifyIcon icon="lucide:settings-2" class="mr-1 size-4" />
        {{ $t('utils.fileBrowser.manageStorage') }}
      </ElButton>
    </div>
    <div class="file-browser__toolbar">
      <div class="file-browser__toolbar-left">
        <span class="file-browser__label">{{
          $t('utils.fileBrowser.storage')
        }}</span>
        <ElSelect
          v-model="selectedConfigId"
          :placeholder="$t('utils.fileBrowser.selectStorage')"
          :aria-label="$t('utils.fileBrowser.storage')"
          :disabled="uploading > 0"
          class="file-browser__config-select"
          @change="handleConfigChange"
        >
          <ElOption
            v-for="config in configList"
            :key="config.id"
            :label="`${config.name}${config.master ? ` (${$t('utils.fileBrowser.default')})` : ''}`"
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
          :placeholder="$t('utils.fileBrowser.search')"
          class="file-browser__search"
          @clear="clearSearch"
          @keyup.enter="handleSearchFiles"
        >
          <template #append>
            <ElButton
              :aria-label="$t('utils.fileBrowser.search')"
              :disabled="!hasConfig"
              @click="handleSearchFiles"
            >
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
          <ElButton
            :disabled="!hasConfig"
            :loading="uploading > 0"
            type="primary"
          >
            <IconifyIcon icon="lucide:upload" class="mr-1 size-4" />
            {{ $t('utils.fileBrowser.upload') }}
          </ElButton>
        </ElUpload>

        <ElButton
          v-if="canCreate"
          :disabled="!hasConfig || mutationLoading"
          @click="showCreateFolder = true"
        >
          <IconifyIcon icon="lucide:folder-plus" class="mr-1 size-4" />
          {{ $t('utils.fileBrowser.newFolder') }}
        </ElButton>

        <ElButton
          v-if="canDelete && selectedCount > 0"
          :loading="mutationLoading"
          type="danger"
          @click="handleBatchDelete"
        >
          <IconifyIcon icon="lucide:trash-2" class="mr-1 size-4" />
          {{ $t('utils.fileBrowser.deleteSelected') }} ({{ selectedCount }})
        </ElButton>

        <ElButtonGroup>
          <ElTooltip
            :content="$t('utils.fileBrowser.listView')"
            placement="bottom"
          >
            <ElButton
              :aria-label="$t('utils.fileBrowser.listView')"
              :type="viewMode === 'list' ? 'primary' : 'default'"
              @click="viewMode = 'list'"
            >
              <IconifyIcon icon="lucide:list" class="size-4" />
            </ElButton>
          </ElTooltip>
          <ElTooltip
            :content="$t('utils.fileBrowser.gridView')"
            placement="bottom"
          >
            <ElButton
              :aria-label="$t('utils.fileBrowser.gridView')"
              :type="viewMode === 'grid' ? 'primary' : 'default'"
              @click="viewMode = 'grid'"
            >
              <IconifyIcon icon="lucide:grid-2x2" class="size-4" />
            </ElButton>
          </ElTooltip>
        </ElButtonGroup>

        <ElTooltip
          :content="$t('utils.fileBrowser.refresh')"
          placement="bottom"
        >
          <ElButton
            :aria-label="$t('utils.fileBrowser.refresh')"
            :loading="loading"
            @click="refresh"
          >
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
      <ElTooltip :content="$t('utils.fileBrowser.parent')" placement="bottom">
        <ElButton
          :aria-label="$t('utils.fileBrowser.parent')"
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
      <ElSelect
        v-model="sortBy"
        class="file-browser__sort"
        :aria-label="$t('utils.fileBrowser.sortName')"
      >
        <ElOption value="name" :label="$t('utils.fileBrowser.sortName')" />
        <ElOption
          value="modified"
          :label="$t('utils.fileBrowser.sortModified')"
        />
        <ElOption value="size" :label="$t('utils.fileBrowser.sortSize')" />
      </ElSelect>
    </div>

    <Loading
      v-if="loading"
      :spinning="loading"
      class="min-h-0 flex-1"
      aria-busy="true"
    />

    <div v-else-if="loadFailed" class="file-browser__empty">
      <ElAlert
        v-if="errorMessage"
        :title="errorMessage"
        type="error"
        :closable="false"
      />
      <ElButton @click="refresh">{{ $t('utils.fileBrowser.retry') }}</ElButton>
    </div>

    <div v-else-if="!hasConfig" class="file-browser__empty">
      <ElEmpty
        :description="$t('utils.fileBrowser.noStorage')"
        :image-size="96"
      />
      <ElButton
        v-if="canManageStorage"
        type="primary"
        @click="router.push('/infra/file/config')"
      >
        {{ $t('utils.fileBrowser.manageStorage') }}
      </ElButton>
    </div>

    <div v-else-if="objects.length === 0" class="file-browser__empty">
      <ElEmpty
        :description="
          $t(
            searchKeyword
              ? 'utils.fileBrowser.noResults'
              : 'utils.fileBrowser.empty',
          )
        "
        :image-size="96"
      />
      <span v-if="!searchKeyword">{{ $t('utils.fileBrowser.emptyHint') }}</span>
    </div>

    <template v-else>
      <FileListView
        v-if="viewMode === 'list'"
        :can-delete="canDelete"
        :can-update="canUpdate"
        :objects="sortedObjects"
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
        :objects="sortedObjects"
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

    <div class="file-browser__status" aria-live="polite">
      <span v-if="selectedConfig">{{
        `${selectedConfig.name} · ${getStorageLabel(selectedConfig.storage)}`
      }}</span>
      <span v-if="!loading && !loadFailed && hasConfig">{{
        $t('utils.fileBrowser.items', { count: objects.length })
      }}</span>
      <span v-if="selectedCount">{{
        $t('utils.fileBrowser.selected', { count: selectedCount })
      }}</span>
      <span v-if="uploading" class="file-browser__upload-status">{{
        $t('utils.fileBrowser.uploading', { count: uploading })
      }}</span>
    </div>

    <ElDialog
      v-model="showCreateFolder"
      append-to-body
      :title="$t('utils.fileBrowser.newFolder')"
      width="min(420px, 94vw)"
      align-center
    >
      <ElInput
        v-model="newFolderName"
        :placeholder="$t('utils.fileBrowser.folderName')"
        maxlength="255"
        @keyup.enter="confirmCreateFolder"
      />
      <template #footer>
        <ElButton @click="showCreateFolder = false">
          {{ $t('utils.fileBrowser.cancel') }}
        </ElButton>
        <ElButton
          type="primary"
          :loading="mutationLoading"
          @click="confirmCreateFolder"
        >
          {{ $t('utils.fileBrowser.confirm') }}
        </ElButton>
      </template>
    </ElDialog>

    <ElDialog
      v-model="showRename"
      append-to-body
      :title="$t('utils.fileBrowser.rename')"
      width="min(420px, 94vw)"
      align-center
    >
      <ElInput
        v-model="renameNewName"
        :placeholder="$t('utils.fileBrowser.newName')"
        maxlength="255"
        @keyup.enter="confirmRename"
      />
      <template #footer>
        <ElButton @click="showRename = false">
          {{ $t('utils.fileBrowser.cancel') }}
        </ElButton>
        <ElButton
          type="primary"
          :loading="mutationLoading"
          @click="confirmRename"
        >
          {{ $t('utils.fileBrowser.confirm') }}
        </ElButton>
      </template>
    </ElDialog>

    <FilePreviewDialog v-model="showPreview" :file="previewFile" />
  </div>
</template>

<style src="./styles/file-browser.css"></style>
