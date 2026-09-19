<script setup lang="ts">
import type { FormInstance, FormRules } from 'element-plus';

import type { ProfileApi } from '#/api/core/profile';

import { ref, watch } from 'vue';

import {
  ElButton,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElRadioButton,
  ElRadioGroup,
  ElTag,
} from 'element-plus';

import { updateUserProfile } from '#/api/core/profile';
import { DICT_TYPE } from '#/constants/dict-types';
import { $t } from '#/locales';
import { useDictionary } from '#/services/dictionary/context';

interface ProfileBaseForm {
  address: string;
  bio: string;
  email: string;
  mobile: string;
  nickname: string;
  sex?: number;
  skills: string[];
  tags: string[];
  username: string;
}

const props = defineProps<{
  profile?: ProfileApi.UserProfileRespVO;
}>();

const emit = defineEmits<{
  success: [];
}>();

const dictionary = useDictionary();
const formRef = ref<FormInstance>();
const newSkillName = ref('');
const newTagName = ref('');
const sexOptions = dictionary.getDictOptions(
  DICT_TYPE.SYSTEM_USER_SEX,
  'number',
);
const formData = ref<ProfileBaseForm>({
  address: '',
  bio: '',
  email: '',
  mobile: '',
  nickname: '',
  sex: undefined,
  skills: [],
  tags: [],
  username: '',
});

const rules: FormRules<ProfileBaseForm> = {
  email: [{ message: '请输入正确的邮箱', trigger: 'blur', type: 'email' }],
  mobile: [{ len: 11, message: '手机号长度必须为 11 位', trigger: 'blur' }],
  nickname: [{ message: '请输入昵称', required: true, trigger: 'blur' }],
};

function toCleanString(value: string) {
  const text = value.trim();
  return text || undefined;
}

function toCleanList(values: string[]) {
  return values.map((item) => item.trim()).filter(Boolean);
}

function addUnique(values: string[], value: string) {
  const text = value.trim();
  if (text && !values.includes(text)) {
    values.push(text);
  }
}

function removeTag(tag: string) {
  formData.value.tags = formData.value.tags.filter((item) => item !== tag);
}

function addTag() {
  addUnique(formData.value.tags, newTagName.value);
  newTagName.value = '';
}

function removeSkill(skill: string) {
  formData.value.skills = formData.value.skills.filter(
    (item) => item !== skill,
  );
}

function addSkill() {
  addUnique(formData.value.skills, newSkillName.value);
  newSkillName.value = '';
}

async function handleSubmit() {
  await formRef.value?.validate();
  await updateUserProfile({
    address: toCleanString(formData.value.address),
    bio: toCleanString(formData.value.bio),
    email: toCleanString(formData.value.email),
    mobile: toCleanString(formData.value.mobile),
    nickname: toCleanString(formData.value.nickname),
    sex: formData.value.sex,
    skills: toCleanList(formData.value.skills),
    tags: toCleanList(formData.value.tags),
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
    formData.value = {
      address: profile.address ?? '',
      bio: profile.bio ?? '',
      email: profile.email ?? '',
      mobile: profile.mobile ?? '',
      nickname: profile.nickname,
      sex: profile.sex ?? undefined,
      skills: [...(profile.skills ?? [])],
      tags: [...(profile.tags ?? [])],
      username: profile.username,
    };
  },
  { immediate: true },
);
</script>

<template>
  <ElForm
    ref="formRef"
    :model="formData"
    :rules="rules"
    class="max-w-5xl"
    label-position="top"
  >
    <div class="grid grid-cols-1 gap-x-6 md:grid-cols-2">
      <ElFormItem label="用户名" prop="username">
        <ElInput v-model="formData.username" disabled />
      </ElFormItem>

      <ElFormItem label="昵称" prop="nickname">
        <ElInput v-model="formData.nickname" maxlength="30" show-word-limit />
      </ElFormItem>

      <ElFormItem label="手机号码" prop="mobile">
        <ElInput v-model="formData.mobile" clearable />
      </ElFormItem>

      <ElFormItem label="邮箱" prop="email">
        <ElInput v-model="formData.email" clearable />
      </ElFormItem>

      <ElFormItem label="地址" prop="address">
        <ElInput
          v-model="formData.address"
          clearable
          maxlength="255"
          show-word-limit
        />
      </ElFormItem>
    </div>

    <ElFormItem label="性别" prop="sex">
      <ElRadioGroup v-model="formData.sex">
        <ElRadioButton
          v-for="option in sexOptions"
          :key="String(option.value)"
          :value="option.value"
        >
          {{ option.label }}
        </ElRadioButton>
      </ElRadioGroup>
    </ElFormItem>

    <ElFormItem label="个人简介" prop="bio">
      <ElInput
        v-model="formData.bio"
        maxlength="500"
        :rows="4"
        show-word-limit
        type="textarea"
      />
    </ElFormItem>

    <ElFormItem label="技能标签" prop="skills">
      <div class="flex flex-wrap items-center gap-2">
        <ElTag
          v-for="skill in formData.skills"
          :key="skill"
          closable
          type="success"
          @close="removeSkill(skill)"
        >
          {{ skill }}
        </ElTag>
        <ElInput
          v-model="newSkillName"
          class="w-40"
          clearable
          @keyup.enter="addSkill"
        />
        <ElButton @click="addSkill">添加</ElButton>
      </div>
    </ElFormItem>

    <ElFormItem label="用户标签" prop="tags">
      <div class="flex flex-wrap items-center gap-2">
        <ElTag
          v-for="tag in formData.tags"
          :key="tag"
          closable
          @close="removeTag(tag)"
        >
          {{ tag }}
        </ElTag>
        <ElInput
          v-model="newTagName"
          class="w-40"
          clearable
          @keyup.enter="addTag"
        />
        <ElButton @click="addTag">添加</ElButton>
      </div>
    </ElFormItem>

    <ElFormItem>
      <ElButton type="primary" @click="handleSubmit">保存</ElButton>
    </ElFormItem>
  </ElForm>
</template>
