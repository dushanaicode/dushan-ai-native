<script lang="ts" setup>
import type { InfraCodegenApi } from '#/api/infra/codegen';

import { computed, ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { IconifyIcon } from '@vben/icons';
import { downloadFileFromBlobPart } from '@vben/utils';

import { useClipboard } from '@vueuse/core';
import {
  ElButton,
  ElEmpty,
  ElMessage,
  ElTabPane,
  ElTabs,
  ElTooltip,
  ElTree,
} from 'element-plus';

import { previewCodegen } from '#/api/infra/codegen';

defineOptions({ name: 'InfraCodegenPreviewCode' });

interface FileTreeNode {
  children?: FileTreeNode[];
  code?: string;
  id: string;
  label: string;
  path?: string;
}

const loading = ref(false);
const tableName = ref('');
const files = ref<InfraCodegenApi.CodegenPreviewRespVO[]>([]);
const treeData = ref<FileTreeNode[]>([]);
const activeFilePath = ref('');
const openFilePaths = ref<string[]>([]);

const activeFile = computed(() =>
  files.value.find((item) => item.filePath === activeFilePath.value),
);
const activeCode = computed(() => activeFile.value?.code || '');
const activeFileName = computed(() => getFileName(activeFilePath.value));
const activeFileType = computed(() =>
  getFileExtension(activeFilePath.value).toUpperCase(),
);
const openedFiles = computed(() =>
  openFilePaths.value
    .map((path) => files.value.find((item) => item.filePath === path))
    .filter((item): item is InfraCodegenApi.CodegenPreviewRespVO =>
      Boolean(item),
    ),
);
const modalTitle = computed(() =>
  tableName.value ? `代码预览 - ${tableName.value}` : '代码预览',
);

const { copy } = useClipboard({ legacy: true });

function normalizeFilePath(path: string) {
  return path.replaceAll('\\', '/');
}

function normalizePreviewFiles(
  previewFiles: InfraCodegenApi.CodegenPreviewRespVO[],
) {
  return previewFiles
    .map((item) => ({
      ...item,
      filePath: normalizeFilePath(item.filePath),
    }))
    .toSorted((left, right) => left.filePath.localeCompare(right.filePath));
}

function getFileName(path: string) {
  const normalizedPath = normalizeFilePath(path);
  return normalizedPath.split('/').pop() || normalizedPath;
}

function getFileExtension(path: string) {
  const fileName = getFileName(path);
  const dotIndex = fileName.lastIndexOf('.');
  return dotIndex === -1 ? 'text' : fileName.slice(dotIndex + 1);
}

function sortTreeNodes(nodes: FileTreeNode[]): FileTreeNode[] {
  return nodes
    .map((node) => ({
      ...node,
      children: node.children ? sortTreeNodes(node.children) : undefined,
    }))
    .toSorted((left, right) => {
      const leftLeaf = left.path ? 1 : 0;
      const rightLeaf = right.path ? 1 : 0;
      return leftLeaf - rightLeaf || left.label.localeCompare(right.label);
    });
}

function buildFileTree(
  previewFiles: InfraCodegenApi.CodegenPreviewRespVO[],
): FileTreeNode[] {
  const roots: FileTreeNode[] = [];

  for (const file of previewFiles) {
    const parts = file.filePath.split(/[\\/]/).filter(Boolean);
    let currentLevel = roots;
    let currentPath = '';

    parts.forEach((part, index) => {
      currentPath = currentPath ? `${currentPath}/${part}` : part;
      const isLeaf = index === parts.length - 1;
      let node = currentLevel.find((item) => item.id === currentPath);

      if (!node) {
        node = {
          id: currentPath,
          label: part,
          ...(isLeaf
            ? { code: file.code, path: file.filePath }
            : { children: [] }),
        };
        currentLevel.push(node);
      }

      if (!isLeaf) {
        node.children ||= [];
        currentLevel = node.children;
      }
    });
  }

  return sortTreeNodes(roots);
}

function handleNodeClick(node: FileTreeNode) {
  if (node.path) {
    openFile(node.path);
  }
}

async function handleCopyCode() {
  if (!activeCode.value) return;

  try {
    await copy(activeCode.value);
    ElMessage.success('复制成功');
  } catch {
    ElMessage.error('复制失败');
  }
}

async function handleCopyPath() {
  if (!activeFilePath.value) return;

  try {
    await copy(activeFilePath.value);
    ElMessage.success('路径复制成功');
  } catch {
    ElMessage.error('路径复制失败');
  }
}

function handleDownloadCurrentFile() {
  if (!activeFile.value) return;

  downloadFileFromBlobPart({
    fileName: activeFileName.value,
    source: activeFile.value.code,
  });
}

function openFile(filePath: string) {
  if (!openFilePaths.value.includes(filePath)) {
    openFilePaths.value.push(filePath);
  }
  activeFilePath.value = filePath;
}

function handleTabRemove(filePath: string) {
  if (openFilePaths.value.length <= 1) {
    return;
  }

  const removedIndex = openFilePaths.value.indexOf(filePath);
  const nextOpenFilePaths = openFilePaths.value.filter(
    (path) => path !== filePath,
  );
  openFilePaths.value = nextOpenFilePaths;

  if (activeFilePath.value !== filePath) {
    return;
  }

  const nextIndex = Math.min(
    Math.max(removedIndex, 0),
    nextOpenFilePaths.length - 1,
  );
  activeFilePath.value = nextOpenFilePaths[nextIndex] || '';
}

function resetPreview() {
  tableName.value = '';
  files.value = [];
  treeData.value = [];
  openFilePaths.value = [];
  activeFilePath.value = '';
}

const [Modal, modalApi] = useVbenModal({
  footer: false,
  fullscreen: true,
  async onOpenChange(isOpen: boolean) {
    if (!isOpen) {
      resetPreview();
      return;
    }

    resetPreview();
    const data = modalApi.getData() as
      | InfraCodegenApi.CodegenTableRespVO
      | undefined;
    if (!data?.id) return;

    loading.value = true;
    tableName.value = data.tableName;
    try {
      const result = normalizePreviewFiles(await previewCodegen(data.id));
      files.value = result;
      treeData.value = buildFileTree(result);
      const firstFilePath = result[0]?.filePath;
      if (firstFilePath) {
        openFile(firstFilePath);
      }
    } finally {
      loading.value = false;
    }
  },
});
</script>

<template>
  <Modal :title="modalTitle" class="w-4/5">
    <div v-loading="loading" class="code-preview">
      <template v-if="files.length > 0">
        <aside class="code-preview__tree">
          <div class="code-preview__tree-header">
            <span>文件列表</span>
            <span>{{ files.length }} 个文件</span>
          </div>
          <ElTree
            :current-node-key="activeFilePath"
            :data="treeData"
            default-expand-all
            :expand-on-click-node="false"
            highlight-current
            node-key="id"
            @node-click="handleNodeClick"
          />
        </aside>

        <section class="code-preview__content">
          <div class="code-preview__header">
            <div class="code-preview__meta">
              <span class="code-preview__path" :title="activeFilePath">
                {{ activeFilePath }}
              </span>
              <span class="code-preview__type">{{ activeFileType }}</span>
            </div>
            <div class="code-preview__actions">
              <ElTooltip content="复制路径" placement="top">
                <ElButton size="small" @click="handleCopyPath">
                  <IconifyIcon icon="lucide:copy" class="mr-1 size-4" />
                  路径
                </ElButton>
              </ElTooltip>
              <ElTooltip content="下载当前文件" placement="top">
                <ElButton size="small" @click="handleDownloadCurrentFile">
                  <IconifyIcon icon="lucide:download" class="mr-1 size-4" />
                  当前文件
                </ElButton>
              </ElTooltip>
              <ElTooltip content="复制当前代码" placement="top">
                <ElButton size="small" type="primary" @click="handleCopyCode">
                  <IconifyIcon
                    icon="lucide:clipboard-copy"
                    class="mr-1 size-4"
                  />
                  代码
                </ElButton>
              </ElTooltip>
            </div>
          </div>

          <ElTabs
            v-model="activeFilePath"
            class="code-preview__tabs"
            type="card"
            @tab-remove="(name) => handleTabRemove(String(name))"
          >
            <ElTabPane
              v-for="file in openedFiles"
              :key="file.filePath"
              closable
              :label="getFileName(file.filePath)"
              :name="file.filePath"
            >
              <pre class="code-preview__pre"><code>{{ file.code }}</code></pre>
            </ElTabPane>
          </ElTabs>
        </section>
      </template>

      <ElEmpty v-else description="暂无预览代码" />
    </div>
  </Modal>
</template>

<style scoped>
.code-preview {
  display: grid;
  grid-template-columns: minmax(260px, 30%) minmax(0, 1fr);
  gap: 12px;
  height: calc(100vh - 180px);
  min-height: 560px;
}

.code-preview__tree {
  display: flex;
  flex-direction: column;
  overflow: auto;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
}

.code-preview__tree-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.code-preview__tree :deep(.el-tree) {
  flex: 1;
  min-width: max-content;
  padding: 8px;
}

.code-preview__content {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
}

.code-preview__header {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.code-preview__meta {
  display: flex;
  gap: 8px;
  align-items: center;
  min-width: 0;
}

.code-preview__path {
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 13px;
  color: var(--el-text-color-regular);
  white-space: nowrap;
}

.code-preview__type {
  flex-shrink: 0;
  padding: 1px 6px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-light);
  border-radius: 4px;
}

.code-preview__actions {
  display: flex;
  flex-shrink: 0;
  gap: 8px;
  align-items: center;
}

.code-preview__tabs {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
}

.code-preview__tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
}

.code-preview__tabs :deep(.el-tab-pane) {
  height: 100%;
}

.code-preview__pre {
  height: 100%;
  padding: 12px;
  margin: 0;
  overflow: auto;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    monospace;
  font-size: 12px;
  line-height: 1.6;
  color: var(--el-text-color-primary);
  background: var(--el-fill-color-lighter);
}

@media (max-width: 900px) {
  .code-preview {
    grid-template-columns: 1fr;
    height: calc(100vh - 160px);
  }

  .code-preview__tree {
    min-height: 220px;
  }

  .code-preview__header {
    flex-direction: column;
    align-items: stretch;
  }

  .code-preview__actions {
    flex-wrap: wrap;
  }
}
</style>
