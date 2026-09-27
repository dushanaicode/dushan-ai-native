import { createApp, h, nextTick } from 'vue';

import { afterEach, expect, it, vi } from 'vitest';

import { initComponentAdapter } from '../../dushan-admin-frontend/apps/web-ele/src/adapter/component';
import {
  initSetupVbenForm,
  useVbenForm,
} from '../../dushan-admin-frontend/apps/web-ele/src/adapter/form';
import { setupI18n } from '../../dushan-admin-frontend/apps/web-ele/src/locales';
import { usePushTargetFormSchema } from '../../dushan-admin-frontend/apps/web-ele/src/views/system/notification/notice/data';
import { useGridFormSchema as useOperateLogSchema } from '../../dushan-admin-frontend/apps/web-ele/src/views/system/operatelog/data';

const backend = vi.hoisted(() => ({
  departments: vi.fn(),
  users: vi.fn(),
  get: vi.fn(),
}));
vi.mock('#/api/system/dept', () => ({
  getSimpleDeptList: backend.departments,
}));
vi.mock('#/api/system/user', () => ({
  getUserPage: backend.users,
  getUser: backend.get,
}));

const cleanups: Array<() => void> = [];
afterEach(() => {
  for (const cleanup of cleanups.splice(0)) cleanup();
  vi.clearAllMocks();
});

it.each([
  ['通知推送', usePushTargetFormSchema, 'userIds', true, '请选择目标用户'],
  ['操作日志', useOperateLogSchema, 'userId', false, '请选择操作人员'],
] as const)(
  '%s 的真实 Schema 可加载用户、搜索并回填选择值',
  async (_name, schema, field, multiple, placeholder) => {
    const id = '9007199254740993';
    const user = {
      id,
      username: 'tester',
      nickname: '测试用户',
      deptName: '技术部',
    };
    backend.departments.mockResolvedValue([
      { id: '9007199254740994', parentId: '0', name: '技术部' },
    ]);
    backend.users.mockResolvedValue({ items: [user], total: 1 });
    backend.get.mockResolvedValue(user);
    await initComponentAdapter();
    await initSetupVbenForm();
    let form!: ReturnType<typeof useVbenForm>[1];
    const app = createApp({
      setup() {
        const [Form, api] = useVbenForm({
          schema: schema().filter((item) => item.fieldName === field),
          showDefaultActions: false,
        });
        form = api;
        return () => h(Form);
      },
    });
    const errors: unknown[] = [];
    app.config.errorHandler = (error) => errors.push(error);
    await setupI18n(app);
    const container = document.createElement('div');
    document.body.append(container);
    app.mount(container);
    cleanups.push(() => {
      app.unmount();
      container.remove();
    });
    await vi.waitFor(
      () => expect(container.textContent).toContain(placeholder),
      { timeout: 5000 },
    );
    container.querySelector<HTMLElement>('[role="button"]')!.click();
    await vi.waitFor(
      () => {
        expect(backend.users).toHaveBeenCalledOnce();
        expect(
          document.querySelector('.el-table__body')?.textContent,
        ).toContain('测试用户');
      },
      { timeout: 3000 },
    );
    expect(document.querySelector('[role="dialog"] [role="alert"]')).toBeNull();
    expect(backend.departments).toHaveBeenCalledTimes(multiple ? 1 : 0);
    const keyword = document.querySelector<HTMLInputElement>(
      '[role="dialog"] .el-input__inner',
    )!;
    keyword.value = 'tester';
    keyword.dispatchEvent(new Event('input', { bubbles: true }));
    await nextTick();
    [...document.querySelectorAll<HTMLButtonElement>('[role="dialog"] button')]
      .find((button) => button.textContent?.trim() === '搜索')!
      .click();
    await vi.waitFor(() =>
      expect(backend.users).toHaveBeenLastCalledWith({
        deptId: undefined,
        username: 'tester',
        page: 1,
        pageSize: 10,
      }),
    );
    await vi.waitFor(() =>
      expect(
        document.querySelector('.el-table__body tbody tr')?.textContent,
      ).toContain('测试用户'),
    );
    document.querySelector<HTMLElement>('.el-table__body tbody tr')!.click();
    await nextTick();
    document
      .querySelector<HTMLButtonElement>(
        '[role="dialog"] .el-dialog__footer .el-button--primary',
      )!
      .click();
    await vi.waitFor(async () =>
      expect((await form.getValues())[field]).toEqual(multiple ? [id] : id),
    );
    expect(errors).toEqual([]);
  },
);
