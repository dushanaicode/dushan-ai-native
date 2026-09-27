<script setup lang="ts">
import type { DeptNode } from '#/components/user-select/selection';

import { onBeforeUnmount, onMounted, ref } from 'vue';

import { ElTreeSelect } from 'element-plus';

import { notifyError } from '#/api/error-feedback';
import { parseDepartments } from '#/components/user-select/selection';
import { createUserSelectPorts } from '#/services/user-select/ports';

defineOptions({ name: 'NativeDeptSelect' });
const model = defineModel<string | string[]>();
const data = ref<DeptNode[]>([]);
const loading = ref(false);
const controller = new AbortController();
onMounted(async () => {
  loading.value = true;
  try {
    data.value = parseDepartments(
      await createUserSelectPorts().departments(controller.signal),
    );
  } catch (error) {
    notifyError(error);
  } finally {
    loading.value = false;
  }
});
onBeforeUnmount(() => controller.abort());
</script>

<template>
  <ElTreeSelect
    v-model="model"
    :data="data"
    :loading="loading"
    node-key="value"
    check-strictly
    clearable
    filterable
    class="w-full"
  />
</template>
