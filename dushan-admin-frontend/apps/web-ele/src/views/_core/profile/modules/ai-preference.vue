<script setup lang="ts">
import type { FormInstance } from 'element-plus';

import type { ProfileApi } from '#/api/core/profile';

import { ref, watch } from 'vue';

import {
  ElButton,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElOption,
  ElSelect,
  ElSwitch,
} from 'element-plus';

import { updateUserProfile } from '#/api/core/profile';
import { $t } from '#/locales';

interface AiPreferenceForm {
  aiPreference: {
    autoSummary: boolean;
    language: string;
    preferredFormat: string;
    responseStyle: string;
    tone: string;
  };
  communicationStyle?: string;
  expertise: string;
  workScope: string;
}

const props = defineProps<{
  profile?: ProfileApi.UserProfileRespVO;
}>();

const emit = defineEmits<{
  success: [];
}>();

const formRef = ref<FormInstance>();
const formData = ref<AiPreferenceForm>({
  aiPreference: {
    autoSummary: false,
    language: 'zh-CN',
    preferredFormat: 'paragraph',
    responseStyle: 'balanced',
    tone: 'professional',
  },
  communicationStyle: undefined,
  expertise: '',
  workScope: '',
});

const communicationStyleOptions = [
  { label: '正式', value: 'formal' },
  { label: '随意', value: 'casual' },
  { label: '技术', value: 'technical' },
];
const responseStyleOptions = [
  { label: '简洁', value: 'concise' },
  { label: '详细', value: 'detailed' },
  { label: '平衡', value: 'balanced' },
];
const formatOptions = [
  { label: '表格', value: 'table' },
  { label: '列表', value: 'list' },
  { label: '段落', value: 'paragraph' },
];
const languageOptions = [
  { label: '中文', value: 'zh-CN' },
  { label: 'English', value: 'en-US' },
];
const toneOptions = [
  { label: '专业', value: 'professional' },
  { label: '友好', value: 'friendly' },
  { label: '随意', value: 'casual' },
];

function toCleanString(value: string) {
  const text = value.trim();
  return text || undefined;
}

async function handleSubmit() {
  await formRef.value?.validate();
  await updateUserProfile({
    aiPreference: formData.value.aiPreference,
    communicationStyle: formData.value.communicationStyle as
      | 'casual'
      | 'formal'
      | 'technical'
      | undefined,
    expertise: toCleanString(formData.value.expertise),
    workScope: toCleanString(formData.value.workScope),
  });
  ElMessage.success($t('ui.actionMessage.operationSuccess'));
  emit('success');
}

watch(
  () => props.profile,
  (profile) => {
    if (!profile) {
      return;
    }
    const preference = profile.aiPreference ?? {};
    formData.value = {
      aiPreference: {
        autoSummary: Boolean(preference.autoSummary),
        language: String(preference.language || 'zh-CN'),
        preferredFormat: String(preference.preferredFormat || 'paragraph'),
        responseStyle: String(preference.responseStyle || 'balanced'),
        tone: String(preference.tone || 'professional'),
      },
      communicationStyle: profile.communicationStyle ?? undefined,
      expertise: profile.expertise ?? '',
      workScope: profile.workScope ?? '',
    };
  },
  { immediate: true },
);
</script>

<template>
  <ElForm
    ref="formRef"
    :model="formData"
    class="max-w-5xl"
    label-position="top"
  >
    <div class="grid grid-cols-1 gap-x-6 md:grid-cols-2">
      <ElFormItem label="工作职责" prop="workScope" class="md:col-span-2">
        <ElInput
          v-model="formData.workScope"
          maxlength="500"
          :rows="3"
          show-word-limit
          type="textarea"
          placeholder="描述日常工作职责，帮助 AI 理解工作场景"
        />
      </ElFormItem>

      <ElFormItem label="专业领域" prop="expertise">
        <ElInput
          v-model="formData.expertise"
          maxlength="500"
          show-word-limit
          placeholder="例如：微服务架构、前端工程化、数据分析"
        />
      </ElFormItem>

      <ElFormItem label="沟通风格" prop="communicationStyle">
        <ElSelect
          v-model="formData.communicationStyle"
          clearable
          placeholder="请选择沟通风格"
        >
          <ElOption
            v-for="option in communicationStyleOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </ElSelect>
      </ElFormItem>
    </div>

    <ElFormItem label="回复语言" prop="language">
      <ElSelect v-model="formData.aiPreference.language" class="w-60">
        <ElOption
          v-for="option in languageOptions"
          :key="option.value"
          :label="option.label"
          :value="option.value"
        />
      </ElSelect>
    </ElFormItem>

    <ElFormItem label="回复风格" prop="responseStyle">
      <ElSelect v-model="formData.aiPreference.responseStyle" class="w-60">
        <ElOption
          v-for="option in responseStyleOptions"
          :key="option.value"
          :label="option.label"
          :value="option.value"
        />
      </ElSelect>
    </ElFormItem>

    <ElFormItem label="语气" prop="tone">
      <ElSelect v-model="formData.aiPreference.tone" class="w-60">
        <ElOption
          v-for="option in toneOptions"
          :key="option.value"
          :label="option.label"
          :value="option.value"
        />
      </ElSelect>
    </ElFormItem>

    <ElFormItem label="偏好格式" prop="preferredFormat">
      <ElSelect v-model="formData.aiPreference.preferredFormat" class="w-60">
        <ElOption
          v-for="option in formatOptions"
          :key="option.value"
          :label="option.label"
          :value="option.value"
        />
      </ElSelect>
    </ElFormItem>

    <ElFormItem label="自动摘要" prop="autoSummary">
      <ElSwitch v-model="formData.aiPreference.autoSummary" />
    </ElFormItem>

    <ElFormItem>
      <ElButton type="primary" @click="handleSubmit">保存</ElButton>
    </ElFormItem>
  </ElForm>
</template>
