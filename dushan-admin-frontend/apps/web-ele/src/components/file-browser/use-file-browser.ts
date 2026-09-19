import type {
  BreadcrumbItem,
  FileConfigSimple,
  FileObject,
  ListObjectsResp,
  ViewMode,
} from './typing';

import { computed, ref } from 'vue';

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
  const viewMode = ref<ViewMode>('list');
  const selectedKeys = ref<string[]>([]);
  const configList = ref<FileConfigSimple[]>([]);
  const selectedConfigId = ref<'' | string>('');
  const searchKeyword = ref('');

  const breadcrumbs = computed<BreadcrumbItem[]>(() => {
    const parts = currentPrefix.value.split('/').filter(Boolean);
    const crumbs: BreadcrumbItem[] = [{ name: '根目录', prefix: '' }];
    let accumulated = '';

    for (const part of parts) {
      accumulated += `${part}/`;
      crumbs.push({ name: part, prefix: accumulated });
    }

    return crumbs;
  });

  const hasConfig = computed(() => configId.value !== null);
  const selectedCount = computed(() => selectedKeys.value.length);

  async function loadConfigList() {
    configList.value = await getSimpleFileConfigList();

    const master = configList.value.find((item) => item.master);
    const defaultConfig = master || configList.value[0];
    if (defaultConfig?.id) {
      selectedConfigId.value = defaultConfig.id;
      await selectConfig(defaultConfig.id);
    }
  }

  async function loadObjects(prefix = '') {
    if (!configId.value) {
      return;
    }

    loading.value = true;
    try {
      const response: ListObjectsResp = await listObjects({
        configId: configId.value,
        prefix,
      });
      objects.value = response.objects || [];
      currentPrefix.value = prefix;
      selectedKeys.value = [];
    } finally {
      loading.value = false;
    }
  }

  async function selectConfig(id: string) {
    configId.value = id;
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
      return;
    }
    await uploadFile(file, currentPrefix.value || undefined, configId.value);
    await refresh();
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
    if (!configId.value) {
      return;
    }

    const normalizedKeyword = keyword.trim();
    if (!normalizedKeyword) {
      searchKeyword.value = '';
      await loadObjects(currentPrefix.value);
      return;
    }

    searchKeyword.value = normalizedKeyword;
    loading.value = true;
    try {
      const response = await searchFiles({
        configId: configId.value,
        keyword: normalizedKeyword,
        page: 1,
        pageSize: 100,
        prefix: currentPrefix.value,
        searchMode: 'fuzzy',
      });
      objects.value = response.items.map((item) => ({
        isDirectory: false,
        key: item.path,
        lastModified: item.createTime,
        name: item.name,
        size: item.size,
        type: item.type,
        url: item.url,
      }));
      selectedKeys.value = [];
    } finally {
      loading.value = false;
    }
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
    loadObjects,
    loading,
    navigateTo,
    objects,
    openItem,
    refresh,
    searchKeyword,
    selectConfig,
    selectedConfigId,
    selectedCount,
    selectedKeys,
    toggleSelect,
    toggleSelectAll,
    viewMode,
  };
}
