<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue';

import { z } from '@vben/common-ui';

import { ElOption, ElSelect } from 'element-plus';

import { notifyError } from '#/api/error-feedback';
import { requestClient } from '#/api/request';
import { $t } from '#/locales';

defineOptions({ name: 'NativeApiSelect' });
const props = withDefaults(
  defineProps<{
    apiPath?: string;
    labelField?: string;
    valueField?: string;
    multiple?: boolean;
  }>(),
  {
    apiPath: '',
    labelField: 'name',
    valueField: 'id',
    multiple: false,
  },
);
const model = defineModel<(number | string)[] | number | string>();
const options = ref<{ label: string; value: number | string }[]>([]);
const loading = ref(false);
let controller: AbortController;
watch(
  () => [props.apiPath, props.labelField, props.valueField],
  async () => {
    controller?.abort();
    const request = new AbortController();
    controller = request;
    options.value = [];
    if (!props.apiPath) {
      loading.value = false;
      return;
    }
    loading.value = true;
    try {
      if (!/^\/(?:system|infra)\/[\w/-]+$/.test(props.apiPath))
        throw new Error($t('infraTools.invalidApi'));
      const rows = z
        .array(z.record(z.string(), z.unknown()))
        .parse(
          await requestClient.get(props.apiPath, { signal: request.signal }),
        );
      request.signal.throwIfAborted();
      options.value = rows.map((row) => ({
        label: z.string().parse(row[props.labelField]),
        value: z.union([z.string(), z.number()]).parse(row[props.valueField]),
      }));
    } catch (error) {
      if (!request.signal.aborted) notifyError(error);
    } finally {
      if (controller === request) loading.value = false;
    }
  },
  { immediate: true },
);
onBeforeUnmount(() => controller?.abort());
</script>

<template>
  <ElSelect
    v-model="model"
    :multiple="multiple"
    :loading="loading"
    filterable
    clearable
    class="w-full"
  >
    <ElOption
      v-for="option in options"
      :key="option.value"
      :value="option.value"
      :label="option.label"
    />
  </ElSelect>
</template>
