<script lang="ts" setup>
import type { DataSourceUrlConfig, DataSourceUrlProps } from './typing';

import { computed, reactive, ref, watch } from 'vue';

import {
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElOption,
  ElSelect,
  ElTabPane,
  ElTabs,
} from 'element-plus';

import {
  buildDatabaseUrl,
  databaseTypes,
  getDatabaseType,
  parseDatabaseUrl,
} from './url';

defineOptions({ name: 'DataSourceUrl' });

const props = withDefaults(defineProps<DataSourceUrlProps>(), {
  dbType: 'mysql',
  modelValue: '',
});
const emit = defineEmits<{
  'update:dbType': [value: string];
  'update:modelValue': [value: string];
}>();
const activeTab = ref('config');

function emptyConfig(dbType: string): DataSourceUrlConfig {
  return {
    dbType,
    database: '',
    host: 'localhost',
    password: '',
    port: getDatabaseType(dbType)?.port,
    query: '',
    username: '',
  };
}

const urlConfig = reactive(emptyConfig(props.dbType));
const currentDatabase = computed(() => getDatabaseType(urlConfig.dbType));
let applyingUrl = false;

function applyConfig(config: DataSourceUrlConfig) {
  applyingUrl = true;
  try {
    Object.assign(urlConfig, config);
  } finally {
    applyingUrl = false;
  }
}

function emitConnection() {
  if (!currentDatabase.value?.enabled) return;
  emit('update:dbType', urlConfig.dbType);
  emit('update:modelValue', buildDatabaseUrl(urlConfig));
}

watch(
  urlConfig,
  () => {
    if (!applyingUrl) emitConnection();
  },
  { deep: true, flush: 'sync' },
);

watch(
  () => props.dbType,
  (type) => {
    if (type !== urlConfig.dbType) applyConfig(emptyConfig(type));
  },
);

watch(
  () => props.modelValue,
  (value) => {
    if (!value) {
      applyConfig(emptyConfig(props.dbType));
      return;
    }
    try {
      const parsed = parseDatabaseUrl(value, urlConfig.dbType);
      applyConfig(parsed);
      if (parsed.dbType !== props.dbType) emit('update:dbType', parsed.dbType);
    } catch {
      // 手动输入可能尚未完整；保留原文，由提交校验提示，不猜测驱动或改写 URL。
    }
  },
  { immediate: true },
);

function onUrlInput(value: string) {
  emit('update:modelValue', value);
}

function onDbTypeChange(value: string) {
  const database = getDatabaseType(value);
  if (!database?.enabled) return;
  applyConfig({ ...urlConfig, dbType: value, port: database.port, query: '' });
  emitConnection();
}
</script>

<template>
  <div class="data-source-url rounded-md border border-border p-4">
    <ElTabs v-model="activeTab" type="card">
      <ElTabPane label="URL配置" name="config">
        <ElForm :model="urlConfig" label-width="100px">
          <ElFormItem label="数据库类型">
            <ElSelect
              :model-value="urlConfig.dbType"
              class="w-full"
              placeholder="请选择数据库类型"
              @change="onDbTypeChange"
            >
              <ElOption
                v-for="item in databaseTypes"
                :key="item.value"
                :label="item.enabled ? item.label : `${item.label}（未启用）`"
                :disabled="!item.enabled"
                :value="item.value"
              />
            </ElSelect>
          </ElFormItem>

          <ElFormItem label="连接模式">
            <span>异步连接</span>
          </ElFormItem>

          <ElFormItem label="主机地址">
            <ElInput
              v-model="urlConfig.host"
              :disabled="!currentDatabase?.enabled"
              placeholder="请输入主机地址"
            />
          </ElFormItem>

          <ElFormItem label="端口">
            <ElInputNumber
              v-model="urlConfig.port"
              :disabled="!currentDatabase?.enabled"
              :max="65535"
              :min="1"
            />
          </ElFormItem>

          <ElFormItem label="数据库名">
            <ElInput
              v-model="urlConfig.database"
              :disabled="!currentDatabase?.enabled"
              placeholder="请输入数据库名"
            />
          </ElFormItem>

          <ElFormItem label="用户名">
            <ElInput
              v-model="urlConfig.username"
              :disabled="!currentDatabase?.enabled"
              autocomplete="off"
              name="database-username"
              placeholder="请输入用户名"
            />
          </ElFormItem>

          <ElFormItem label="密码">
            <ElInput
              v-model="urlConfig.password"
              :disabled="!currentDatabase?.enabled"
              autocomplete="new-password"
              name="database-password"
              placeholder="请输入密码"
              show-password
              type="password"
            />
          </ElFormItem>
        </ElForm>
      </ElTabPane>

      <ElTabPane label="生成的 URL" name="url">
        <ElInput
          :model-value="modelValue"
          :rows="4"
          placeholder="自动生成的数据库连接 URL"
          type="textarea"
          @input="onUrlInput"
        />
      </ElTabPane>
    </ElTabs>
  </div>
</template>

<style scoped>
.data-source-url {
  width: 100%;
}
</style>
