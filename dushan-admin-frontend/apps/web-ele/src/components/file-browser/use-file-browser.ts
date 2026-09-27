import type {
  BreadcrumbItem,
  FileConfigSimple,
  FileObject,
  ViewMode,
} from './typing';

import { computed, onScopeDispose, ref } from 'vue';

import { $t } from '@vben/locales';

import { takeErrorMessage } from '#/api/error-feedback';
import {
  createDirectory,
  deleteByKey,
  deleteByKeys,
  listObjects,
  renameFile,
  searchFiles,
  uploadFile,
} from '#/api/infra/file';
import { getSimpleFileConfigList } from '#/api/infra/file-config';

export function useFileBrowser() {
  const configId = ref<null | string>(null);
  const currentPrefix = ref('');
  const objects = ref<FileObject[]>([]);
  const loading = ref(false);
  const loadFailed = ref(false);
  const errorMessage = ref('');
  const uploading = ref(0);
  const viewMode = ref<ViewMode>('list');
  const sortBy = ref<'modified' | 'name' | 'size'>('name');
  const selectedKeys = ref<string[]>([]);
  const configList = ref<FileConfigSimple[]>([]);
  const selectedConfigId = ref<'' | string>('');
  const searchKeyword = ref('');
  let request: AbortController | undefined;
  let active = true;
  onScopeDispose(() => {
    active = false;
    request?.abort();
  });

  const breadcrumbs = computed<BreadcrumbItem[]>(() => {
    const parts = currentPrefix.value.split('/').filter(Boolean);
    const crumbs: BreadcrumbItem[] = [
      { name: $t('utils.fileBrowser.root'), prefix: '' },
    ];
    let accumulated = '';

    for (const part of parts) {
      accumulated += `${part}/`;
      crumbs.push({ name: part, prefix: accumulated });
    }

    return crumbs;
  });

  const hasConfig = computed(() => configId.value !== null);
  const selectedCount = computed(() => selectedKeys.value.length);
  const selectedConfig = computed(() =>
    configList.value.find((item) => item.id === configId.value),
  );
  const sortedObjects = computed(() =>
    objects.value.toSorted((left, right) => {
      const directories =
        Number(Boolean(right.isDirectory)) - Number(Boolean(left.isDirectory));
      if (directories) return directories;
      if (sortBy.value === 'size') return (right.size ?? 0) - (left.size ?? 0);
      if (sortBy.value === 'modified') {
        return (
          (right.lastModified ? Date.parse(right.lastModified) : 0) -
          (left.lastModified ? Date.parse(left.lastModified) : 0)
        );
      }
      return left.name.localeCompare(right.name, undefined, { numeric: true });
    }),
  );

  function startQuery() {
    request?.abort();
    request = new AbortController();
    loading.value = true;
    loadFailed.value = false;
    errorMessage.value = '';
    return request;
  }

  function report(error: unknown) {
    loadFailed.value = true;
    errorMessage.value = takeErrorMessage(
      error,
      $t('utils.fileBrowser.loadFailed'),
    );
  }

  async function loadConfigList() {
    const controller = startQuery();
    try {
      const configs = await getSimpleFileConfigList({
        signal: controller.signal,
        errorMessageMode: 'form',
      });
      if (controller.signal.aborted) return;
      configList.value = configs;
      const selected =
        configs.find((item) => item.id === selectedConfigId.value) ??
        configs.find((item) => item.master) ??
        configs[0];
      if (selected) await selectConfig(selected.id);
      else {
        configId.value = null;
        selectedConfigId.value = '';
        objects.value = [];
      }
    } catch (error) {
      if (!controller.signal.aborted) report(error);
    } finally {
      if (request === controller) loading.value = false;
    }
  }

  async function loadObjects(prefix = '', keyword = '') {
    if (!configId.value) {
      return;
    }

    const controller = startQuery();
    const id = configId.value;
    currentPrefix.value = prefix;
    searchKeyword.value = keyword;
    selectedKeys.value = [];
    objects.value = [];
    const options = {
      signal: controller.signal,
      errorMessageMode: 'form' as const,
    };
    try {
      let entries: FileObject[];
      if (keyword) {
        const result = await searchFiles(
          {
            configId: id,
            keyword,
            page: 1,
            pageSize: 100,
            prefix,
            searchMode: 'fuzzy',
          },
          options,
        );
        entries = result.items.map((item) => ({
          isDirectory: false,
          key: item.path,
          lastModified: item.createTime,
          name: item.name,
          size: item.size,
          type: item.type,
          url: item.url,
        }));
      } else {
        const result = await listObjects({ configId: id, prefix }, options);
        entries = result.objects;
      }
      if (!controller.signal.aborted) objects.value = entries;
    } catch (error) {
      if (!controller.signal.aborted) report(error);
    } finally {
      if (request === controller) loading.value = false;
    }
  }

  async function selectConfig(id: string) {
    configId.value = id;
    selectedConfigId.value = id;
    currentPrefix.value = '';
    await loadObjects('');
  }

  async function handleConfigChange(value: '' | string) {
    selectedConfigId.value = value;
    if (value !== '') {
      await selectConfig(value);
    }
  }

  async function navigateTo(prefix: string) {
    await loadObjects(prefix);
  }

  async function goUp() {
    const parts = currentPrefix.value.split('/').filter(Boolean);
    parts.pop();
    await loadObjects(parts.length > 0 ? `${parts.join('/')}/` : '');
  }

  async function openItem(item: FileObject) {
    if (item.isDirectory) {
      await navigateTo(item.key);
    }
  }

  async function refresh() {
    if (!hasConfig.value) {
      await loadConfigList();
      return;
    }
    if (searchKeyword.value.trim()) {
      await handleSearch(searchKeyword.value);
      return;
    }

    await loadObjects(currentPrefix.value);
  }

  async function handleCreateDirectory(folderName: string) {
    if (!configId.value || !folderName) {
      return;
    }
    await createDirectory({
      configId: configId.value,
      directoryPath: `${currentPrefix.value}${folderName}/`,
    });
    await refresh();
  }

  async function handleUploadFile(file: File) {
    if (!configId.value) {
      throw new Error($t('utils.fileBrowser.selectStorage'));
    }
    const id = configId.value;
    const directory = currentPrefix.value;
    uploading.value++;
    try {
      await uploadFile(file, directory || undefined, id);
      if (active && configId.value === id && currentPrefix.value === directory)
        await refresh();
    } finally {
      uploading.value--;
    }
  }

  async function handleDeleteItem(key: string) {
    if (!configId.value) {
      return;
    }
    await deleteByKey(configId.value, key);
    await refresh();
  }

  async function handleDeleteBatch() {
    if (!configId.value || selectedKeys.value.length === 0) {
      return;
    }

    const keys = objects.value
      .filter((item) => selectedKeys.value.includes(item.key))
      .map((item) => item.key);

    if (keys.length > 0) {
      await deleteByKeys(configId.value, keys);
    }
    selectedKeys.value = [];
    await refresh();
  }

  function toggleSelect(key: string) {
    const index = selectedKeys.value.indexOf(key);
    if (index === -1) {
      selectedKeys.value.push(key);
    } else {
      selectedKeys.value.splice(index, 1);
    }
  }

  function toggleSelectAll() {
    selectedKeys.value =
      selectedKeys.value.length === objects.value.length
        ? []
        : objects.value.map((item) => item.key);
  }

  function handleDownloadItem(item: FileObject) {
    if (!item.url) {
      return;
    }
    const link = document.createElement('a');
    link.href = item.url;
    link.download = item.name;
    link.style.display = 'none';
    document.body.append(link);
    link.click();
    link.remove();
  }

  async function handleRenameItem(oldKey: string, newName: string) {
    if (!configId.value || !newName) {
      return;
    }
    await renameFile({ configId: configId.value, newName, oldKey });
    await refresh();
  }

  async function handleSearch(keyword: string) {
    await loadObjects(currentPrefix.value, keyword.trim());
  }

  async function clearSearch() {
    searchKeyword.value = '';
    await loadObjects(currentPrefix.value);
  }

  return {
    breadcrumbs,
    clearSearch,
    configId,
    configList,
    currentPrefix,
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
    loadObjects,
    loading,
    navigateTo,
    objects,
    openItem,
    refresh,
    searchKeyword,
    selectedConfig,
    selectConfig,
    selectedConfigId,
    selectedCount,
    selectedKeys,
    sortBy,
    sortedObjects,
    toggleSelect,
    toggleSelectAll,
    uploading,
    viewMode,
  };
}
