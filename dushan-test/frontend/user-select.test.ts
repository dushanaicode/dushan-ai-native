import { createApp, h, nextTick, ref } from 'vue';

import { $t } from '@vben/locales';

import { ElMessage } from 'element-plus';
import { afterEach, expect, it, vi } from 'vitest';

import { BusinessError } from '../../dushan-admin-frontend/apps/web-ele/src/api/business-error';
import { notifyError } from '../../dushan-admin-frontend/apps/web-ele/src/api/error-feedback';
import UserSelectFormField from '../../dushan-admin-frontend/apps/web-ele/src/components/user-select/user-select-form-field.vue';
import UserSelectModal from '../../dushan-admin-frontend/apps/web-ele/src/components/user-select/user-select-modal.vue';

const largeId = '18446744073709551615';
const disposers: Array<() => void> = [];
afterEach(() => {
  for (const dispose of disposers.splice(0)) dispose();
  vi.restoreAllMocks();
});
function mount(render: () => ReturnType<typeof h>) {
  const container = document.createElement('div');
  document.body.append(container);
  const app = createApp({ render });
  const errors: unknown[] = [];
  app.config.errorHandler = (error) => errors.push(error);
  app.mount(container);
  disposers.push(() => {
    app.unmount();
    container.remove();
  });
  return { container, errors };
}
function ports() {
  return {
    departments: vi.fn(async () => [
      { value: '0', label: '部门', children: [] },
    ]),
    selected: vi.fn(async (ids: string[]) =>
      ids.map((id) => ({ id, label: `用户${id}` })),
    ),
    users: vi.fn(async () => ({
      items: [{ id: '0', label: '零用户' }],
      total: 1,
    })),
  };
}
it('可选用户字段接受后端的null，回填和清空不破坏渲染', async () => {
  const loaders = ports();
  const value = ref<null | string>(null);
  const { container, errors } = mount(() =>
    h(UserSelectFormField, { modelValue: value.value, ports: loaders }),
  );
  await nextTick();
  expect(errors).toEqual([]);
  expect(loaders.selected).not.toHaveBeenCalled();
  value.value = largeId;
  await vi.waitFor(() =>
    expect(container.textContent).toContain(`用户${largeId}`),
  );
  value.value = null;
  await vi.waitFor(() =>
    expect(container.textContent).not.toContain(`用户${largeId}`),
  );
  expect(errors).toEqual([]);
});
it('用户选择横幅使用后端原文，外层error监听不再重复弹窗', async () => {
  const message = vi
    .spyOn(ElMessage, 'error')
    .mockImplementation(() => ({ close: vi.fn() }));
  const loaders = ports();
  loaders.departments.mockRejectedValueOnce(
    new BusinessError(
      {
        code: 400,
        message: '此部门不允许选择用户',
        data: null,
        error: null,
      },
      {},
    ),
  );
  mount(() =>
    h(UserSelectModal, {
      visible: true,
      modelValue: largeId,
      ports: loaders,
      onError: (error: unknown) => notifyError(error, '外层固定失败'),
    }),
  );
  await vi.waitFor(() => {
    const alerts = document.querySelectorAll('[role="dialog"] [role="alert"]');
    expect(alerts).toHaveLength(1);
    expect(alerts[0].textContent).toContain('此部门不允许选择用户');
  });
  expect(message).not.toHaveBeenCalled();
});
it('请求层已经提示后不重复横幅，但保留重试入口', async () => {
  const message = vi
    .spyOn(ElMessage, 'error')
    .mockImplementation(() => ({ close: vi.fn() }));
  const failure = new BusinessError(
    { code: 400, message: '部门服务暂不可用', data: null, error: null },
    {},
  );
  notifyError(failure);
  const loaders = ports();
  loaders.departments.mockRejectedValueOnce(failure);
  mount(() =>
    h(UserSelectModal, { visible: true, modelValue: largeId, ports: loaders }),
  );
  let retry: HTMLButtonElement | undefined;
  await vi.waitFor(() => {
    retry = [
      ...document.querySelectorAll<HTMLButtonElement>('[role="dialog"] button'),
    ].find(
      (button) => button.textContent?.trim() === $t('utils.userSelect.retry'),
    );
    expect(retry).toBeDefined();
  });
  expect(document.querySelector('[role="dialog"] [role="alert"]')).toBeNull();
  expect(message).toHaveBeenCalledExactlyOnceWith('部门服务暂不可用');
  retry!.click();
  await vi.waitFor(() => expect(loaders.departments).toHaveBeenCalledTimes(2));
});
it('初始化失败后可以同时重试部门和所选用户，恢复确认', async () => {
  const loaders = ports();
  const confirmed = vi.fn();
  loaders.departments.mockRejectedValueOnce(
    new Error('department unavailable'),
  );
  mount(() =>
    h(UserSelectModal, {
      visible: true,
      modelValue: largeId,
      ports: loaders,
      onConfirm: confirmed,
    }),
  );
  await vi.waitFor(() =>
    expect(
      document.querySelector('[role="dialog"] [role="alert"]'),
    ).not.toBeNull(),
  );
  const confirm = document.querySelector<HTMLButtonElement>(
    '[role="dialog"] .el-dialog__footer .el-button--primary',
  )!;
  expect(confirm.disabled).toBe(true);
  document
    .querySelector<HTMLButtonElement>('[role="dialog"] [role="alert"] button')!
    .click();
  await vi.waitFor(() => expect(confirm.disabled).toBe(false));
  expect(loaders.departments).toHaveBeenCalledTimes(2);
  confirm.click();
  expect(confirmed.mock.calls[0]![0]).toBe(largeId);
});
it('真实用户选择弹窗保留大ID与0字符串，确认后才修改表单', async () => {
  const value = ref<string | string[]>([largeId]);
  const loaders = ports();
  const { container, errors } = mount(() =>
    h(UserSelectFormField, {
      modelValue: value.value,
      ports: loaders,
      deptId: '0',
      multiple: true,
      'onUpdate:modelValue': (next) => {
        value.value = next as string[];
      },
    }),
  );
  await vi.waitFor(() =>
    expect(container.textContent).toContain(`用户${largeId}`),
  );
  container.querySelector<HTMLElement>('[role="button"]')!.click();
  await vi.waitFor(() =>
    expect(
      document.querySelector('.el-table__body tbody tr')?.textContent,
    ).toContain('零用户'),
  );
  expect(loaders.users.mock.calls[0]![0]).toMatchObject({
    deptId: '0',
    page: 1,
    pageSize: 10,
  });
  document.querySelector<HTMLElement>('.el-table__body tbody tr')!.click();
  await nextTick();
  expect(value.value).toEqual([largeId]);
  document
    .querySelector<HTMLButtonElement>(
      '[role="dialog"] .el-dialog__footer .el-button--primary',
    )!
    .click();
  await nextTick();
  expect(value.value).toEqual([largeId, '0']);
  expect(errors).toEqual([]);
});
it('后发查询优先，旧结果与关闭后的响应均不能覆盖当前页面', async () => {
  const visible = ref(true);
  const first = Promise.withResolvers<{
    items: { id: string; label: string }[];
    total: number;
  }>();
  const second = Promise.withResolvers<{
    items: { id: string; label: string }[];
    total: number;
  }>();
  const loaders = ports();
  const signals: AbortSignal[] = [];
  loaders.users.mockImplementation((_query, signal) => {
    signals.push(signal);
    return signals.length === 1 ? first.promise : second.promise;
  });
  const { errors } = mount(() =>
    h(UserSelectModal, {
      visible: visible.value,
      ports: loaders,
      showDeptFilter: false,
      'onUpdate:visible': (next) => {
        visible.value = next;
      },
    }),
  );
  await vi.waitFor(() => expect(loaders.users).toHaveBeenCalledOnce());
  const search = [
    ...document.querySelectorAll<HTMLButtonElement>('[role="dialog"] button'),
  ].find((button) => button.textContent?.includes('utils.userSelect.search'))!;
  search.click();
  expect(signals[0]!.aborted).toBe(true);
  second.resolve({ items: [{ id: 'fresh', label: '新结果' }], total: 1 });
  await vi.waitFor(() =>
    expect(document.querySelector('.el-table__body')?.textContent).toContain(
      '新结果',
    ),
  );
  first.resolve({ items: [{ id: 'stale', label: '旧结果' }], total: 1 });
  await nextTick();
  await nextTick();
  expect(document.querySelector('.el-table__body')?.textContent).not.toContain(
    '旧结果',
  );
  visible.value = false;
  await nextTick();
  expect(signals[1]!.aborted).toBe(true);
  expect(errors).toEqual([]);
});
it('初值标签读取失败可见，disabled阻止打开和清空；迟到标签不会串值', async () => {
  const value = ref<string | string[]>(largeId);
  const loaders = ports();
  const first = Promise.withResolvers<{ id: string; label: string }[]>();
  loaders.selected.mockImplementationOnce(() => first.promise);
  const disabled = ref(false);
  const { container, errors } = mount(() =>
    h(UserSelectFormField, {
      modelValue: value.value,
      ports: loaders,
      disabled: disabled.value,
      'onUpdate:modelValue': (next) => {
        value.value = next as string;
      },
    }),
  );
  value.value = '0';
  await nextTick();
  await vi.waitFor(() => expect(container.textContent).toContain('用户0'));
  first.resolve([{ id: largeId, label: '过时标签' }]);
  await nextTick();
  expect(container.textContent).not.toContain('过时标签');
  loaders.selected.mockRejectedValueOnce(new Error('lookup failed'));
  value.value = 'next';
  await vi.waitFor(() =>
    expect(container.querySelector('[role="alert"]')).not.toBeNull(),
  );
  disabled.value = true;
  await nextTick();
  container.querySelector<HTMLElement>('[role="button"]')!.click();
  expect(loaders.users).not.toHaveBeenCalled();
  expect(value.value).toBe('next');
  expect(errors).toEqual([]);
});
