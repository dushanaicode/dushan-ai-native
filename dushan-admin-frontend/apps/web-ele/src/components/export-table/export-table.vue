<script setup lang="ts">
import type { ExportTableData } from './task';

import { computed, onUnmounted, ref, shallowRef } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { $t } from '@vben/locales';

import {
  ElAlert,
  ElButton,
  ElCheckbox,
  ElOption,
  ElSelect,
} from 'element-plus';

import { exportColumns, ExportTask } from './task';

const emit = defineEmits<{ close: []; success: []; error: [error: unknown] }>();
const data = shallowRef<ExportTableData>();
const fields = ref<string[]>([]);
const failed = ref(false);
const task = new ExportTask();
const columns = computed(() =>
  data.value ? exportColumns(data.value.columns) : [],
);
const all = computed({
  get: () =>
    columns.value.length > 0 && columns.value.length === fields.value.length,
  set: (value) => {
    fields.value = value ? columns.value.map((column) => column.field) : [];
  },
});
const [Modal, modal] = useVbenModal({
  footer: false,
  onBeforeClose() {
    task.cancel();
    return true;
  },
  onOpenChange(open) {
    if (!open) {
      task.cancel();
      emit('close');
    }
  },
});
function setData(value: ExportTableData) {
  task.cancel();
  data.value = value;
  fields.value = exportColumns(value.columns).map((column) => column.field);
  failed.value = false;
}
async function submit() {
  failed.value = false;
  try {
    await task.run(data.value as ExportTableData, fields.value);
    modal.close();
    emit('success');
  } catch (error) {
    if (!(error instanceof DOMException && error.name === 'AbortError')) {
      failed.value = true;
      emit('error', error);
    }
  }
}
onUnmounted(() => task.cancel());
defineExpose({ setData, open: modal.open, close: modal.close });
</script>

<template>
  <Modal :title="$t('utils.export.title')">
    <ElAlert
      v-if="failed"
      :title="$t('utils.export.failed')"
      type="error"
      :closable="false"
    />
    <ElSelect v-model="fields" multiple class="w-full" :disabled="task.loading">
      <ElOption
        v-for="column in columns"
        :key="column.field"
        :label="column.title"
        :value="column.field"
      />
    </ElSelect>
    <div class="mt-4 flex items-center justify-between">
      <ElCheckbox
        v-model="all"
        :disabled="task.loading"
        :indeterminate="fields.length > 0 && !all"
      >
        <span>{{ $t('utils.export.all') }}</span>
        <span>({{ fields.length }}/{{ columns.length }})</span>
      </ElCheckbox>
      <div>
        <ElButton @click="modal.close()">
          <span>{{ $t('utils.export.cancel') }}</span>
        </ElButton>
        <ElButton
          type="primary"
          :loading="task.loading"
          :disabled="!data || fields.length === 0"
          @click="submit"
        >
          <span>{{ $t('utils.export.title') }}</span>
        </ElButton>
      </div>
    </div>
  </Modal>
</template>
