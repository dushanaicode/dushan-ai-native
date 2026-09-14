<script setup lang="ts">
import type { FileAccess, FileUploadProps, FileValue } from './files';

import {
  computed,
  onUnmounted,
  ref,
  shallowRef,
  useTemplateRef,
  watch,
} from 'vue';

import { $t } from '@vben/locales';
import { downloadFileFromUrl } from '@vben/utils';

import { ElAlert, ElButton, ElDialog, ElImage, ElProgress } from 'element-plus';

import { fileIds, parseFileAccess, UploadQueue } from './files';

const props = withDefaults(defineProps<FileUploadProps>(), {
  accept: '',
  buttonText: undefined,
  helpText: undefined,
  listType: 'text',
  maxNumber: 1,
  maxSize: 10,
  multiple: false,
  showDescription: false,
  showFileList: true,
});
const emit = defineEmits<{
  change: [value: FileValue];
  error: [error: unknown];
}>();
const model = defineModel<FileValue>();
const input = useTemplateRef<HTMLInputElement>('input');
const failed = ref(false);
const access = shallowRef(new Map<string, FileAccess>());
const preview = ref('');
const previewOpen = ref(false);
const accept = computed(() =>
  Array.isArray(props.accept) ? props.accept.join(',') : props.accept,
);
const arrayValue = computed(() => props.multiple || props.maxNumber > 1);
const queue = new UploadQueue({
  ports: () => props.ports,
  limits: () => ({
    accept: accept.value,
    maxNumber: props.maxNumber,
    maxSize: props.maxSize,
  }),
  write: (ids) => {
    model.value = arrayValue.value ? ids : ids[0];
    emit('change', model.value);
  },
});
let controller = new AbortController();
let previewController = new AbortController();
watch(model, (value) => queue.sync(fileIds(value)), {
  immediate: true,
  deep: true,
});
watch(
  () => props.ports,
  () => queue.cancelAll(),
);
watch(
  () => [queue.ids, props.ports] as const,
  () => {
    previewController.abort();
    previewOpen.value = false;
    preview.value = '';
    void load();
  },
  { immediate: true },
);
async function load() {
  controller.abort();
  controller = new AbortController();
  const signal = controller.signal;
  access.value = new Map();
  failed.value = false;
  if (queue.ids.length === 0) return;
  const ids = [...queue.ids];
  try {
    const records = parseFileAccess(
      await props.ports.resolve(ids, signal),
      ids,
    );
    signal.throwIfAborted();
    access.value = new Map(records.map((file) => [file.id, file]));
  } catch (error) {
    if (!signal.aborted) report(error);
  }
}
function report(error: unknown) {
  failed.value = true;
  emit('error', error);
}
async function choose(event: Event) {
  const element = event.target as HTMLInputElement;
  const files = [...(element.files as FileList)];
  element.value = '';
  if (props.disabled) return;
  failed.value = false;
  try {
    await queue.add(files);
  } catch (error) {
    report(error);
  }
}
async function show(id: string) {
  previewController.abort();
  previewController = new AbortController();
  const signal = previewController.signal;
  try {
    const records = parseFileAccess(await props.ports.resolve([id], signal), [
      id,
    ]);
    signal.throwIfAborted();
    const file = records[0] as FileAccess;
    if (file.mediaType.startsWith('image/')) {
      preview.value = file.url;
      previewOpen.value = true;
    } else await downloadFileFromUrl({ source: file.url, fileName: file.name });
  } catch (error) {
    if (!signal.aborted) report(error);
  }
}
onUnmounted(() => {
  queue.dispose();
  controller.abort();
  previewController.abort();
});
defineExpose({ cancel: () => queue.cancelAll() });
</script>

<template>
  <div class="flex flex-col gap-2">
    <input
      ref="input"
      class="hidden"
      type="file"
      :accept="accept"
      :multiple="multiple"
      :disabled="disabled"
      @change="choose"
    />
    <ElButton
      :disabled="disabled || queue.ids.length + queue.jobs.length >= maxNumber"
      @click="input?.click()"
    >
      <slot>
        <span>{{ buttonText ?? $t('utils.upload.choose') }}</span>
      </slot>
    </ElButton>
    <p v-if="helpText">{{ helpText }}</p>
    <p v-else-if="showDescription" class="text-muted-foreground text-sm">
      {{ accept || '*' }} · {{ maxSize }} MB
    </p>
    <ElAlert
      v-if="failed"
      type="error"
      :title="$t('utils.upload.failed')"
      :closable="false"
    >
      <ElButton text @click="load">
        <span>{{ $t('utils.upload.retry') }}</span>
      </ElButton>
    </ElAlert>
    <div
      v-for="job in queue.jobs"
      :key="job.key"
      class="flex items-center gap-2"
    >
      <span class="truncate">{{ job.name }}</span>
      <ElProgress :percentage="job.progress" class="min-w-20 flex-1" />
      <ElButton text @click="queue.cancel(job.key)">
        <span>{{ $t('utils.upload.cancel') }}</span>
      </ElButton>
    </div>
    <template v-if="showFileList">
      <div
        v-for="id in queue.ids"
        :key="id"
        class="flex items-center gap-2 rounded border p-2"
      >
        <ElImage
          v-if="
            listType !== 'text' &&
            access.get(id)?.mediaType.startsWith('image/')
          "
          :src="access.get(id)?.url"
          class="size-16"
          fit="cover"
        />
        <span class="flex-1 truncate">{{ access.get(id)?.name ?? id }}</span>
        <ElButton text @click="show(id)">
          <span>{{ $t('utils.upload.preview') }}</span>
        </ElButton>
        <ElButton
          text
          type="danger"
          :disabled="disabled"
          @click="queue.remove(id)"
        >
          <span>{{ $t('utils.upload.remove') }}</span>
        </ElButton>
      </div>
    </template>
    <ElDialog
      v-model="previewOpen"
      :title="$t('utils.upload.preview')"
      append-to-body
      destroy-on-close
    >
      <ElImage :src="preview" fit="contain" class="w-full" />
    </ElDialog>
  </div>
</template>
