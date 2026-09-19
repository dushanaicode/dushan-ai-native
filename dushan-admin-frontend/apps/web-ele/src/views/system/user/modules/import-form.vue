<script lang="ts" setup>
import type { UploadRawFile } from 'element-plus';

import type { SystemUserApi } from '#/api/system/user';

import { ref } from 'vue';

import { useVbenModal } from '@vben/common-ui';
import { downloadFileFromBlobPart } from '@vben/utils';

import { ElAlert, ElButton, ElMessage, ElSwitch, ElUpload } from 'element-plus';

import { importUser, importUserTemplate } from '#/api/system/user';

const emit = defineEmits<{
  success: [];
}>();

const uploadRef = ref<InstanceType<typeof ElUpload>>();
const file = ref<UploadRawFile>();
const updateSupport = ref(false);
const importResult = ref<SystemUserApi.UserImportRespVO>();

const [Modal, modalApi] = useVbenModal({
  async onConfirm() {
    if (importResult.value) {
      modalApi.close();
      return;
    }

    if (!file.value) {
      ElMessage.warning('请先选择要导入的 Excel 文件');
      return;
    }

    modalApi.lock();
    try {
      importResult.value = await importUser(file.value, updateSupport.value);
      ElMessage.success('导入完成');
      emit('success');
    } finally {
      modalApi.unlock();
    }
  },
  onOpenChange(isOpen) {
    if (!isOpen) {
      file.value = undefined;
      updateSupport.value = false;
      importResult.value = undefined;
      uploadRef.value?.clearFiles();
    }
  },
});

function beforeUpload(rawFile: UploadRawFile) {
  const isExcel =
    rawFile.type ===
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
    rawFile.type === 'application/vnd.ms-excel' ||
    rawFile.name.endsWith('.xls') ||
    rawFile.name.endsWith('.xlsx');
  const isLt10M = rawFile.size / 1024 / 1024 < 10;

  if (!isExcel) {
    ElMessage.error('只允许上传 xls、xlsx 文件');
    return false;
  }
  if (!isLt10M) {
    ElMessage.error('文件大小不能超过 10MB');
    return false;
  }

  file.value = rawFile;
  return false;
}

function onExceed(files: File[]) {
  uploadRef.value?.clearFiles();
  const rawFile = files[0] as undefined | UploadRawFile;
  if (!rawFile) return;
  rawFile.uid = Date.now();
  uploadRef.value?.handleStart(rawFile);
}

function onRemove() {
  file.value = undefined;
}

async function downloadTemplate() {
  const data = await importUserTemplate();
  downloadFileFromBlobPart({ fileName: '用户导入模板.xls', source: data });
}

function formatFailureNames(failureUsernames?: Record<string, string>) {
  if (!failureUsernames) return [];
  return Object.entries(failureUsernames).map(([username, message]) => {
    return `${username}：${message}`;
  });
}
</script>

<template>
  <Modal
    :confirm-button-text="importResult ? '关闭' : '确认导入'"
    :show-cancel-button="!importResult"
    class="w-1/2"
    title="用户导入"
  >
    <div v-if="!importResult" class="space-y-4">
      <ElUpload
        ref="uploadRef"
        :before-upload="beforeUpload"
        :limit="1"
        accept=".xls,.xlsx"
        drag
        @exceed="onExceed"
        @remove="onRemove"
      >
        <div class="flex flex-col items-center gap-2 py-6">
          <span class="text-base">将 Excel 文件拖到此处，或点击选择</span>
          <span class="text-sm text-gray-500">仅支持 xls、xlsx，大小不超过 10MB</span>
        </div>
      </ElUpload>

      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span>更新已存在用户</span>
          <ElSwitch v-model="updateSupport" />
        </div>
        <ElButton link type="primary" @click="downloadTemplate">
          下载模板
        </ElButton>
      </div>
    </div>

    <div v-else class="space-y-4">
      <ElAlert
        :closable="false"
        :title="`新增 ${importResult.createUsernames.length} 个，更新 ${importResult.updateUsernames.length} 个，失败 ${Object.keys(importResult.failureUsernames).length} 个`"
        show-icon
        type="success"
      />

      <ElAlert
        v-if="importResult.createUsernames.length"
        :closable="false"
        :title="`新增成功：${importResult.createUsernames.join('、')}`"
        type="success"
      />
      <ElAlert
        v-if="importResult.updateUsernames.length"
        :closable="false"
        :title="`更新成功：${importResult.updateUsernames.join('、')}`"
        type="success"
      />
      <ElAlert
        v-for="item in formatFailureNames(importResult.failureUsernames)"
        :key="item"
        :closable="false"
        :title="item"
        type="error"
      />
    </div>
  </Modal>
</template>
