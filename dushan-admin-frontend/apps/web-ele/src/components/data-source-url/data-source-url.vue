<script lang="ts" setup>
import type { DataSourceUrlConfig, DataSourceUrlProps } from './typing';

import { computed, onMounted, reactive, ref, watch } from 'vue';

import {
  ElCheckbox,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElOption,
  ElSelect,
  ElTabPane,
  ElTabs,
} from 'element-plus';

import { InfraDbTypeEnum } from '#/constants/enums';

defineOptions({ name: 'DataSourceUrl' });

const props = withDefaults(defineProps<DataSourceUrlProps>(), {
  modelValue: '',
});

const emit = defineEmits<{
  'update:modelValue': [value: string];
}>();

const activeTab = ref('config');

const databases = {
  dm: {
    asyncDriver: 'aioodbc',
    defaultPort: 5236,
    name: '达梦数据库 (DM Database)',
    syncDriver: 'dmPython',
  },
  gaussdb: {
    asyncDriver: 'asyncpg',
    defaultPort: 5432,
    name: '华为 GaussDB',
    syncDriver: 'psycopg2',
  },
  kingbase: {
    asyncDriver: 'asyncpg',
    defaultPort: 54_321,
    name: '人大金仓 (KingbaseES)',
    syncDriver: 'psycopg2',
  },
  mssql: {
    asyncDriver: 'aioodbc',
    defaultPort: 1433,
    name: 'Microsoft SQL Server (微软)',
    syncDriver: 'pyodbc',
  },
  mysql: {
    asyncDriver: 'aiomysql',
    defaultPort: 3306,
    name: 'MySQL/MariaDB',
    syncDriver: 'pymysql',
  },
  oracle: {
    asyncDriver: 'oracledb',
    defaultPort: 1521,
    name: 'Oracle Database (甲骨文)',
    syncDriver: 'cx_oracle',
  },
  postgresql: {
    asyncDriver: 'asyncpg',
    defaultPort: 5432,
    name: 'PostgreSQL',
    syncDriver: 'psycopg2',
  },
} as const;

const dbTypeOptions = Object.values(InfraDbTypeEnum).map((item) => ({
  label: item.label,
  value: item.value,
}));

const defaultUrlConfig: DataSourceUrlConfig = {
  database: '',
  dbType: 'mysql',
  filePath: '',
  host: 'localhost',
  password: '',
  port: 3306,
  schema: '',
  useAsync: true,
  username: '',
};

const urlConfig = reactive<DataSourceUrlConfig>({ ...defaultUrlConfig });

function getCurrentDbConfig(type: string) {
  return databases[type as keyof typeof databases];
}

const generatedUrl = computed(() => {
  const dbConfig = getCurrentDbConfig(urlConfig.dbType);
  if (!dbConfig) return '';

  const encodedPassword = encodeURIComponent(urlConfig.password);

  switch (urlConfig.dbType) {
    case 'dm': {
      const protocol = urlConfig.useAsync ? 'dm+aioodbc' : 'dm+dmPython';
      return `${protocol}://${urlConfig.username}:${encodedPassword}@${urlConfig.host}:${urlConfig.port}/${urlConfig.database}`;
    }
    case 'gaussdb': {
      const protocol = urlConfig.useAsync
        ? 'gaussdb+asyncpg'
        : 'gaussdb+psycopg2';
      return `${protocol}://${urlConfig.username}:${encodedPassword}@${urlConfig.host}:${urlConfig.port}/${urlConfig.database}`;
    }
    case 'kingbase': {
      const protocol = urlConfig.useAsync
        ? 'kingbase+asyncpg'
        : 'kingbase+psycopg2';
      return `${protocol}://${urlConfig.username}:${encodedPassword}@${urlConfig.host}:${urlConfig.port}/${urlConfig.database}`;
    }
    case 'mssql': {
      const protocol = urlConfig.useAsync ? 'mssql+aioodbc' : 'mssql+pyodbc';
      return `${protocol}://${urlConfig.username}:${encodedPassword}@${urlConfig.host}:${urlConfig.port}/${urlConfig.database}`;
    }
    case 'mysql': {
      const protocol = urlConfig.useAsync ? 'mysql+aiomysql' : 'mysql+pymysql';
      return `${protocol}://${urlConfig.username}:${encodedPassword}@${urlConfig.host}:${urlConfig.port}/${urlConfig.database}`;
    }
    case 'oracle': {
      const protocol = urlConfig.useAsync
        ? 'oracle+oracledb'
        : 'oracle+cx_oracle';
      return `${protocol}://${urlConfig.username}:${encodedPassword}@${urlConfig.host}:${urlConfig.port}/${urlConfig.database}`;
    }
    case 'postgresql': {
      const protocol = urlConfig.useAsync
        ? 'postgresql+asyncpg'
        : 'postgresql+psycopg2';
      const schemaPart = urlConfig.schema ? `?schema=${urlConfig.schema}` : '';
      return `${protocol}://${urlConfig.username}:${encodedPassword}@${urlConfig.host}:${urlConfig.port}/${urlConfig.database}${schemaPart}`;
    }
    default: {
      const protocol = urlConfig.useAsync
        ? `${urlConfig.dbType}+${dbConfig.asyncDriver}`
        : `${urlConfig.dbType}+${dbConfig.syncDriver}`;
      return `${protocol}://${urlConfig.username}:${encodedPassword}@${urlConfig.host}:${urlConfig.port}/${urlConfig.database}`;
    }
  }
});

watch(
  () => urlConfig,
  () => {
    emit('update:modelValue', generatedUrl.value);
  },
  { deep: true },
);

watch(
  () => props.modelValue,
  (newVal) => {
    if (newVal) {
      parseUrl(newVal);
    }
  },
);

function parseUrl(url: string) {
  try {
    let normalizedUrl = url;
    let dbType = 'mysql';
    let useAsync = true;

    if (url.includes('+oracledb') || url.includes('+cx_oracle')) {
      dbType = 'oracle';
      useAsync = url.includes('+oracledb');
      normalizedUrl = url.replace(/oracle\+(?:oracledb|cx_oracle)/, 'oracle');
    } else if (url.includes('+aioodbc') && url.includes('mssql')) {
      dbType = 'mssql';
      normalizedUrl = url.replace('mssql+aioodbc', 'mssql');
    } else if (url.includes('+pyodbc') && url.includes('mssql')) {
      dbType = 'mssql';
      useAsync = false;
      normalizedUrl = url.replace('mssql+pyodbc', 'mssql');
    } else if (url.includes('+aiomysql') || url.includes('+pymysql')) {
      dbType = 'mysql';
      useAsync = url.includes('+aiomysql');
      normalizedUrl = url.replace(/mysql\+(?:aiomysql|pymysql)/, 'mysql');
    } else if (url.includes('+asyncpg') && url.includes('postgresql')) {
      dbType = 'postgresql';
      normalizedUrl = url.replace('postgresql+asyncpg', 'postgresql');
    } else if (url.includes('+psycopg2') && url.includes('postgresql')) {
      dbType = 'postgresql';
      useAsync = false;
      normalizedUrl = url.replace('postgresql+psycopg2', 'postgresql');
    } else if (url.includes('dm+aioodbc') || url.includes('dm+dmPython')) {
      dbType = 'dm';
      useAsync = url.includes('dm+aioodbc');
      normalizedUrl = url.replace(/dm\+(?:aioodbc|dmPython)/, 'dm');
    } else if (
      url.includes('kingbase+asyncpg') ||
      url.includes('kingbase+psycopg2')
    ) {
      dbType = 'kingbase';
      useAsync = url.includes('kingbase+asyncpg');
      normalizedUrl = url.replace(/kingbase\+(?:asyncpg|psycopg2)/, 'kingbase');
    } else if (
      url.includes('gaussdb+asyncpg') ||
      url.includes('gaussdb+psycopg2')
    ) {
      dbType = 'gaussdb';
      useAsync = url.includes('gaussdb+asyncpg');
      normalizedUrl = url.replace(/gaussdb\+(?:asyncpg|psycopg2)/, 'gaussdb');
    } else {
      for (const type of Object.keys(databases)) {
        const dbConfig = getCurrentDbConfig(type);
        if (!dbConfig) continue;

        if (url.includes(`+${dbConfig.asyncDriver}`)) {
          dbType = type;
          normalizedUrl = url.replace(`+${dbConfig.asyncDriver}`, '');
          break;
        }

        if (url.includes(`+${dbConfig.syncDriver}`)) {
          dbType = type;
          useAsync = false;
          normalizedUrl = url.replace(`+${dbConfig.syncDriver}`, '');
          break;
        }

        if (url.startsWith(`${type}:`)) {
          dbType = type;
          break;
        }
      }
    }

    const urlObj = new URL(normalizedUrl);

    urlConfig.dbType = dbType;
    urlConfig.useAsync = useAsync;
    urlConfig.host = urlObj.hostname || 'localhost';
    urlConfig.port = urlObj.port
      ? Number.parseInt(urlObj.port)
      : getDefaultPort(dbType);
    urlConfig.username = urlObj.username || '';
    urlConfig.password = urlObj.password
      ? decodeURIComponent(urlObj.password)
      : '';
    urlConfig.database = urlObj.pathname.startsWith('/')
      ? urlObj.pathname.slice(1)
      : urlObj.pathname;
    urlConfig.schema = urlObj.searchParams.get('schema') || '';
  } catch {
    // Keep manual URL input as the source of truth while the user edits.
  }
}

function getDefaultPort(dbType: string): number {
  return getCurrentDbConfig(dbType)?.defaultPort || 3306;
}

onMounted(() => {
  if (props.modelValue) {
    parseUrl(props.modelValue);
  }
});

function onUrlInput(value: string) {
  emit('update:modelValue', value);
}

function onDbTypeChange(value: string) {
  urlConfig.dbType = value;
  urlConfig.port = getDefaultPort(value);
}
</script>

<template>
  <div class="data-source-url rounded-md border border-border p-4">
    <ElTabs v-model="activeTab" type="card">
      <ElTabPane label="URL配置" name="config">
        <ElForm :model="urlConfig" label-width="100px">
          <ElFormItem label="数据库类型">
            <ElSelect
              v-model="urlConfig.dbType"
              class="w-full"
              placeholder="请选择数据库类型"
              @change="onDbTypeChange"
            >
              <ElOption
                v-for="item in dbTypeOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </ElSelect>
          </ElFormItem>

          <ElFormItem label="连接模式">
            <ElCheckbox v-model="urlConfig.useAsync">
              使用异步驱动 (推荐)
            </ElCheckbox>
          </ElFormItem>

          <ElFormItem label="主机地址">
            <ElInput v-model="urlConfig.host" placeholder="请输入主机地址" />
          </ElFormItem>

          <ElFormItem label="端口">
            <ElInputNumber v-model="urlConfig.port" :max="65535" :min="1" />
          </ElFormItem>

          <ElFormItem label="数据库名">
            <ElInput
              v-model="urlConfig.database"
              placeholder="请输入数据库名"
            />
          </ElFormItem>

          <ElFormItem label="用户名">
            <ElInput v-model="urlConfig.username" placeholder="请输入用户名" />
          </ElFormItem>

          <ElFormItem label="密码">
            <ElInput
              v-model="urlConfig.password"
              placeholder="请输入密码"
              show-password
              type="password"
            />
          </ElFormItem>

          <ElFormItem v-if="urlConfig.dbType === 'postgresql'" label="Schema">
            <ElInput v-model="urlConfig.schema" placeholder="请输入 Schema" />
          </ElFormItem>
        </ElForm>
      </ElTabPane>

      <ElTabPane label="生成的 URL" name="url">
        <ElInput
          :model-value="generatedUrl"
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
