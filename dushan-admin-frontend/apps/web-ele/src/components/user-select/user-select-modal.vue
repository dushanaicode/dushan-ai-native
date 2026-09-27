<script setup lang="ts">
import type {
  DeptNode,
  UserRecord,
  UserSelectProps,
  UserValue,
} from './selection';

import { computed, onUnmounted, ref, shallowRef, watch } from 'vue';

import { Loading } from '@vben/common-ui';
import { $t } from '@vben/locales';

import {
  ElAlert,
  ElButton,
  ElCheckbox,
  ElDialog,
  ElInput,
  ElPagination,
  ElRadio,
  ElTable,
  ElTableColumn,
  ElTag,
  ElTreeSelect,
} from 'element-plus';

import { takeErrorMessage } from '#/api/error-feedback';

import {
  parseDepartments,
  parseSelected,
  parseUsers,
  selectionValue,
  toggleUser,
  userIds,
} from './selection';

const props = withDefaults(
  defineProps<UserSelectProps & { visible: boolean; modelValue?: UserValue }>(),
  {
    deptId: undefined,
    placeholder: undefined,
    size: 'default',
    showDeptFilter: true,
    modelValue: undefined,
  },
);
const emit = defineEmits<{
  'update:visible': [value: boolean];
  confirm: [value: UserValue, users: UserRecord[]];
  error: [error: unknown];
}>();
const selected = ref<string[]>([]);
const cache = shallowRef(new Map<string, UserRecord>());
const departments = ref<DeptNode[]>([]);
const rows = ref<UserRecord[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(10);
const keyword = ref('');
const dept = ref<string>();
const loading = ref(false);
const failed = ref('');
const retryAvailable = ref(false);
let initialController = new AbortController();
let queryController = new AbortController();
const selectedUsers = computed(() =>
  selected.value
    .map((id) => cache.value.get(id))
    .filter((user): user is UserRecord => user !== undefined),
);
watch(
  () =>
    [
      props.visible,
      props.modelValue,
      props.ports,
      props.deptId,
      props.multiple,
    ] as const,
  () => {
    initialController.abort();
    queryController.abort();
    rows.value = [];
    departments.value = [];
    cache.value = new Map();
    total.value = 0;
    loading.value = false;
    if (!props.visible) return;
    selected.value = userIds(props.modelValue);
    dept.value = props.deptId;
    page.value = 1;
    keyword.value = '';
    failed.value = '';
    retryAvailable.value = false;
    initialController = new AbortController();
    const signal = initialController.signal;
    void initialize(signal);
    void search();
  },
  { immediate: true, deep: true },
);
function remember(users: UserRecord[]) {
  cache.value = new Map([
    ...cache.value,
    ...users.map((user) => [user.id, user] as const),
  ]);
}
function report(error: unknown) {
  retryAvailable.value = true;
  failed.value = takeErrorMessage(error, $t('utils.userSelect.failed'));
  emit('error', error);
}
async function initialize(signal: AbortSignal) {
  const ids = [...selected.value];
  try {
    const [depts, users] = await Promise.all([
      props.showDeptFilter
        ? props.ports.departments(signal)
        : Promise.resolve([]),
      ids.length > 0 ? props.ports.selected(ids, signal) : Promise.resolve([]),
    ]);
    signal.throwIfAborted();
    departments.value = parseDepartments(depts);
    remember(parseSelected(users, ids));
  } catch (error) {
    if (!signal.aborted) report(error);
  }
}
async function search() {
  queryController.abort();
  queryController = new AbortController();
  const signal = queryController.signal;
  loading.value = true;
  rows.value = [];
  failed.value = '';
  retryAvailable.value = false;
  try {
    const data = parseUsers(
      await props.ports.users(
        {
          deptId: props.deptId ?? dept.value,
          keyword: keyword.value.trim(),
          page: page.value,
          pageSize: pageSize.value,
        },
        signal,
      ),
    );
    signal.throwIfAborted();
    rows.value = data.items;
    total.value = data.total;
    remember(data.items);
  } catch (error) {
    if (!signal.aborted) report(error);
  } finally {
    if (!signal.aborted) loading.value = false;
  }
}
function filter() {
  page.value = 1;
  void search();
}
function retry() {
  initialController.abort();
  initialController = new AbortController();
  void initialize(initialController.signal);
  void search();
}
function toggle(row: UserRecord) {
  if (!props.disabled)
    selected.value = toggleUser(selected.value, row.id, props.multiple);
}
function close() {
  initialController.abort();
  queryController.abort();
  emit('update:visible', false);
}
function confirm() {
  if (props.disabled || selectedUsers.value.length !== selected.value.length)
    return;
  emit(
    'confirm',
    selectionValue(selected.value, props.multiple),
    selectedUsers.value,
  );
  close();
}
onUnmounted(() => {
  initialController.abort();
  queryController.abort();
});
</script>

<template>
  <ElDialog
    :model-value="visible"
    :title="$t('utils.userSelect.title')"
    width="min(860px, 95vw)"
    class="user-select-dialog flex h-[min(720px,calc(100dvh-32px))] flex-col"
    body-class="flex min-h-0 flex-1 flex-col overflow-hidden"
    header-class="shrink-0"
    footer-class="shrink-0"
    align-center
    append-to-body
    @update:model-value="
      (open) => {
        if (!open) close();
      }
    "
  >
    <div class="flex min-h-0 flex-1 flex-col gap-3">
      <div class="flex shrink-0 flex-wrap gap-2">
        <ElTreeSelect
          v-if="showDeptFilter"
          v-model="dept"
          :data="departments"
          node-key="value"
          check-strictly
          clearable
          :value-on-clear="undefined"
          :disabled="deptId !== undefined || disabled"
          :placeholder="$t('utils.userSelect.department')"
          class="w-full sm:!w-60"
          @change="filter"
        />
        <ElInput
          v-model="keyword"
          :placeholder="$t('utils.userSelect.keyword')"
          :disabled="disabled"
          class="!w-auto min-w-0 flex-1"
          @keyup.enter="filter"
        />
        <ElButton :disabled="disabled" @click="filter">
          <span>{{ $t('utils.userSelect.search') }}</span>
        </ElButton>
      </div>
      <ElAlert
        v-if="failed"
        :title="failed"
        type="error"
        :closable="false"
        class="shrink-0"
      >
        <ElButton text @click="retry">
          <span>{{ $t('utils.userSelect.retry') }}</span>
        </ElButton>
      </ElAlert>
      <ElButton v-if="retryAvailable && !failed" text @click="retry">
        <span>{{ $t('utils.userSelect.retry') }}</span>
      </ElButton>
      <div
        v-if="selected.length"
        class="flex max-h-[min(96px,15dvh)] shrink-0 flex-wrap gap-2 overflow-y-auto"
      >
        <ElTag
          v-for="id in selected"
          :key="id"
          :closable="!disabled"
          @close="selected = selected.filter((value) => value !== id)"
        >
          {{ cache.get(id)?.label ?? id }}
        </ElTag>
      </div>
      <Loading :spinning="loading" :aria-busy="loading" class="min-h-0 flex-1">
        <ElTable
          :data="rows"
          row-key="id"
          height="100%"
          :aria-busy="loading"
          @row-click="toggle"
        >
          <ElTableColumn width="50">
            <template #default="{ row }">
              <ElCheckbox
                v-if="multiple"
                :model-value="selected.includes(row.id)"
                :disabled="disabled"
                :aria-label="row.label"
                @click.stop
                @change="toggle(row as UserRecord)"
              /><ElRadio
                v-else
                :model-value="selected[0]"
                :value="row.id"
                :disabled="disabled"
                :aria-label="row.label"
                @click.stop
                @change="toggle(row as UserRecord)"
              >
                <span></span>
              </ElRadio>
            </template>
          </ElTableColumn>
          <ElTableColumn prop="label" :label="$t('utils.userSelect.user')" />
          <ElTableColumn
            prop="description"
            :label="$t('utils.userSelect.description')"
          />
          <ElTableColumn prop="id" label="ID" />
        </ElTable>
      </Loading>
      <ElPagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :pager-count="5"
        :total="total"
        class="shrink-0 flex-wrap gap-y-2"
        layout="total, sizes, prev, pager, next"
        @current-change="search"
        @size-change="filter"
      />
    </div>
    <template #footer>
      <ElButton @click="close">
        <span>{{ $t('utils.userSelect.cancel') }}</span>
      </ElButton>
      <ElButton
        type="primary"
        :disabled="disabled || selectedUsers.length !== selected.length"
        @click="confirm"
      >
        <span>{{ $t('utils.userSelect.confirm') }}</span>
      </ElButton>
    </template>
  </ElDialog>
</template>
