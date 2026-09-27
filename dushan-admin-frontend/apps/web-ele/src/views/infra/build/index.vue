<script setup lang="ts">
import type { Config } from '@form-create/designer';
import type { Rule } from '@form-create/element-ui';

import { computed, getCurrentInstance, onMounted, ref } from 'vue';

import { Page, useVbenModal } from '@vben/common-ui';
import { preferences } from '@vben/preferences';

import FcDesigner from '@form-create/designer';
import english from '@form-create/designer/locale/en.es.js';
import formCreate from '@form-create/element-ui';
import { useClipboard } from '@vueuse/core';
import { ElButton, ElInput, ElMessage } from 'element-plus';

import { notifyError } from '#/api/error-feedback';
import { nativeFormRules } from '#/components/form-create/rules';
import { setupFormCreate } from '#/components/form-create/setup';
import { $t } from '#/locales';

import { createVueForm } from './export';

defineOptions({ name: 'InfraBuild' });
const instance = getCurrentInstance();
if (!instance) throw new Error('?????????????????');
setupFormCreate(instance.appContext.app);
const designer = ref<InstanceType<typeof FcDesigner>>();
const locale = computed(() =>
  preferences.app.locale === 'en-US' ? english : undefined,
);
const config: Config = {
  autoActive: true,
  useTemplate: false,
  showSaveBtn: false,
  showAi: false,
  hiddenItem: ['upload', 'fc-editor'],
  formOptions: { form: { labelWidth: '100px' } },
};
const [CodeModal, codeModal] = useVbenModal({ footer: false });
const [ImportModal, importModal] = useVbenModal({ onConfirm: importRules });
const code = ref('');
const title = ref('');
const fileName = ref('');
const input = ref('');
const importError = ref('');
const { copy } = useClipboard({ legacy: true });

function showCode(kind: 'component' | 'options' | 'rules') {
  const editor = designer.value;
  if (!editor) return;
  title.value = $t(`infraTools.${kind}`);
  fileName.value =
    kind === 'component' ? 'GeneratedForm.vue' : `form-${kind}.json`;
  switch (kind) {
    case 'component': {
      code.value = createVueForm(editor.getRule(), editor.getOption());
      break;
    }
    case 'options': {
      code.value = JSON.stringify(editor.getOption(), null, 2);
      break;
    }
    case 'rules': {
      code.value = formCreate.toJson(editor.getRule());
      break;
    }
  }
  codeModal.open();
}
async function copyCode() {
  try {
    await copy(code.value);
    ElMessage.success($t('infraTools.copied'));
  } catch (error) {
    notifyError(error);
  }
}
function downloadCode() {
  const href = URL.createObjectURL(
    new Blob([code.value], { type: 'text/plain;charset=utf-8' }),
  );
  const anchor = document.createElement('a');
  anchor.href = href;
  anchor.download = fileName.value;
  anchor.click();
  URL.revokeObjectURL(href);
}
function openImport() {
  input.value = '';
  importError.value = '';
  importModal.open();
}
function importRules() {
  const editor = designer.value;
  if (!editor) return;
  let rules: unknown;
  try {
    rules = JSON.parse(input.value);
  } catch {
    importError.value = $t('infraTools.invalidImport');
    return;
  }
  if (
    !Array.isArray(rules) ||
    rules.some(
      (rule) =>
        !rule || typeof rule !== 'object' || typeof rule.type !== 'string',
    )
  ) {
    importError.value = $t('infraTools.invalidImport');
    return;
  }
  editor.setRule(rules as Rule[]);
  importModal.close();
  ElMessage.success($t('infraTools.imported'));
}
onMounted(() => {
  const editor = designer.value;
  if (!editor) throw new Error('????????');
  const rules = nativeFormRules();
  editor.addComponent(rules);
  editor.addMenu({
    name: 'native',
    title: $t('infraTools.customFields'),
    list: rules.map(({ name, label, icon }) => ({ name, label, icon })),
  });
});
</script>

<template>
  <Page auto-content-height>
    <div
      class="form-builder h-full min-h-0 overflow-hidden rounded-md border bg-background"
    >
      <FcDesigner
        ref="designer"
        height="100%"
        :config="config"
        :locale="locale"
      >
        <template #handle>
          <ElButton size="small" @click="openImport">
            <span>{{ $t('infraTools.import') }}</span>
          </ElButton>
          <ElButton size="small" @click="showCode('rules')">
            <span>{{ $t('infraTools.rules') }}</span>
          </ElButton>
          <ElButton size="small" @click="showCode('options')">
            <span>{{ $t('infraTools.options') }}</span>
          </ElButton>
          <ElButton size="small" type="primary" @click="showCode('component')">
            <span>{{ $t('infraTools.component') }}</span>
          </ElButton>
        </template>
      </FcDesigner>
    </div>
    <CodeModal :title="title" class="w-[min(900px,95vw)]">
      <div class="mb-3 flex justify-end gap-2">
        <ElButton @click="downloadCode">
          <span>{{ $t('infraTools.download') }}</span>
        </ElButton>
        <ElButton type="primary" @click="copyCode">
          <span>{{ $t('infraTools.copy') }}</span>
        </ElButton>
      </div>
      <pre
        class="max-h-[65vh] overflow-auto whitespace-pre-wrap rounded bg-muted p-4 text-sm"
      ><code>{{ code }}</code></pre>
    </CodeModal>
    <ImportModal
      :title="$t('infraTools.import')"
      :confirm-text="$t('infraTools.apply')"
      class="w-[min(800px,95vw)]"
    >
      <ElInput v-model="input" type="textarea" :rows="15" />
      <p v-if="importError" role="alert" class="mt-2 text-destructive">
        {{ importError }}
      </p>
    </ImportModal>
  </Page>
</template>

<style scoped>
/* stylelint-disable selector-class-pattern -- form-create既有类名，仅在本页面适配主题。 */
.form-builder :deep(._fc-designer),
.form-builder :deep(._fc-l),
.form-builder :deep(._fc-m),
.form-builder :deep(._fc-r),
.form-builder :deep(._fc-m-tools),
.form-builder :deep(._fc-m-drag),
.form-builder :deep(.drag-holder),
.form-builder :deep(._fc-m-input-handle),
.form-builder :deep(.draggable-drag),
.form-builder :deep(._fc-l-close),
.form-builder :deep(._fc-r-close),
.form-builder :deep(._fc-l-open),
.form-builder :deep(._fc-r-open) {
  color: var(--el-text-color-primary);
  background: var(--el-bg-color);
  border-color: var(--el-border-color);
}

.form-builder :deep(._fc-l-label),
.form-builder :deep(._fc-l-tab),
.form-builder :deep(._fc-r-title),
.form-builder :deep(._fc-r .el-form-item__label),
.form-builder :deep(._fc-l .el-tree-node__label),
.form-builder :deep(._fc-r-tab-props ._fd-ci-head) {
  color: var(--el-text-color-primary);
}

.form-builder :deep(._fc-l-item),
.form-builder :deep(._fc-m .form-create ._fc-l-item) {
  color: var(--el-text-color-primary);
  background: var(--el-fill-color-light);
  border-color: var(--el-border-color);
}

.form-builder :deep(._fc-l-menu),
.form-builder :deep(._fc-l-group),
.form-builder :deep(._fc-l-tabs),
.form-builder :deep(._fc-r-tabs) {
  border-color: var(--el-border-color);
}

.form-builder :deep(._fc-m-tools) {
  min-height: 40px;
}

.form-builder :deep(._fc-m-tools-r) {
  padding: 4px;
}

.form-builder :deep(._fc-m-con) {
  background: var(--el-fill-color-light);
}

.form-builder :deep(.drag-holder::after),
.form-builder :deep(._fc-child-empty::after) {
  color: var(--el-text-color-secondary);
}

:global(.el-dialog._fd-preview-dialog) {
  display: flex;
  flex-direction: column;
  max-height: 90vh;
  margin: 5vh auto;
}

:global(._fd-preview-dialog .el-dialog__body) {
  min-height: 0;
  overflow: auto;
}
</style>
