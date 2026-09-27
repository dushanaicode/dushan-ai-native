import { createApp, h, nextTick, ref } from 'vue';

import { setupI18n } from '@vben/locales';

import { afterEach, describe, expect, it, vi } from 'vitest';

import { initComponentAdapter } from '../../dushan-admin-frontend/apps/web-ele/src/adapter/component';
import {
  initSetupVbenForm,
  useVbenForm,
} from '../../dushan-admin-frontend/apps/web-ele/src/adapter/form';
import { provideDictionary } from '../../dushan-admin-frontend/apps/web-ele/src/services/dictionary/context';
import { DictionaryRuntime } from '../../dushan-admin-frontend/apps/web-ele/src/services/dictionary/runtime';
import { SessionCoordinator } from '../../dushan-admin-frontend/apps/web-ele/src/services/session/coordinator';
import { useTypeFormSchema as configSchema } from '../../dushan-admin-frontend/apps/web-ele/src/views/infra/config/data';
import { useFormSchema as mqSchema } from '../../dushan-admin-frontend/apps/web-ele/src/views/infra/mq/data';
import { useFormSchema as deptSchema } from '../../dushan-admin-frontend/apps/web-ele/src/views/system/dept/data';
import { useFormSchema as mailAccountSchema } from '../../dushan-admin-frontend/apps/web-ele/src/views/system/mail/account/data';
import { useFormSchema as oauthSchema } from '../../dushan-admin-frontend/apps/web-ele/src/views/system/oauth2/client/data';
import { useFormSchema as smsChannelSchema } from '../../dushan-admin-frontend/apps/web-ele/src/views/system/sms/channel/data';
import { useFormSchema as socialClientSchema } from '../../dushan-admin-frontend/apps/web-ele/src/views/system/social/client/data';
import {
  useFormSchema,
  useGridFormSchema,
} from '../../dushan-admin-frontend/apps/web-ele/src/views/system/user/data';

vi.mock('#/services/user-select/ports', () => ({
  createUserSelectPorts: () => ({}),
}));
vi.mock('#/services/file/ports', () => ({ createFilePorts: () => ({}) }));

vi.mock('#/api/system/dept', () => ({
  getSimpleDeptList: async () => [
    { id: '9007199254740993', parentId: '0', name: '测试公司' },
    { id: '9007199254740994', parentId: '9007199254740993', name: '技术部' },
  ],
}));
vi.mock('#/api/system/post', () => ({
  getSimplePostList: async () => [{ id: '9007199254740995', name: '工程师' }],
}));
vi.mock('#/api/system/role', () => ({ getSimpleRoleList: async () => [] }));

const cleanups: Array<() => void> = [];
afterEach(() => {
  for (const cleanup of cleanups.splice(0)) cleanup();
});

async function mountForm(
  search = false,
  schemaFactory = search ? useGridFormSchema : useFormSchema,
) {
  await initComponentAdapter();
  await initSetupVbenForm();
  const scope = { generation: 'ui-test', token: 'fixture' };
  const session = new SessionCoordinator({
    read: () => scope,
    write: vi.fn(),
    expire: async () => {},
    refresh: async () => '',
    lock: (operation) => operation(),
    subscribe: () => () => {},
  });
  const loader = vi.fn(async () => [
    { dictType: 'system_user_sex', value: '1', label: '男' },
    { dictType: 'system_user_sex', value: '2', label: '女' },
    { dictType: 'common_status', value: '1', label: '启用' },
  ]);
  const dictionary = new DictionaryRuntime({
    session,
    locale: ref('zh-CN'),
    loader,
  });
  let api!: ReturnType<typeof useVbenForm>[1];
  const app = createApp({
    setup() {
      const [Form, formApi] = useVbenForm({
        schema: schemaFactory(),
        showDefaultActions: false,
      });
      api = formApi;
      return () => h(Form);
    },
  });
  const errors: unknown[] = [];
  app.config.errorHandler = (error) => errors.push(error);
  await setupI18n(app);
  provideDictionary(app, dictionary);
  const container = document.createElement('div');
  document.body.append(container);
  app.mount(container);
  cleanups.push(() => {
    app.unmount();
    container.remove();
    session.dispose();
  });
  await vi.waitFor(
    () => {
      expect(errors).toEqual([]);
      expect(container.querySelector('input')).not.toBeNull();
    },
    { timeout: 5000 },
  );
  return { api, container, dictionary, errors, loader };
}

describe('业务 Schema 使用真实注册组件', () => {
  it.each([
    ['MQ初始消费者列表', mqSchema, 'consumer'],
    ['OAuth自定义标签', oauthSchema, 'scopes'],
  ] as const)(
    '%s 初次渲染提供空选项，不触发Select异常',
    async (_, factory, fieldName) => {
      const { errors, api } = await mountForm(false, () =>
        factory().filter((field) => field.fieldName === fieldName),
      );
      await api.setValues({
        [fieldName]: fieldName === 'scopes' ? ['read'] : 'consumer',
      });
      await nextTick();
      expect(errors).toEqual([]);
    },
  );
  it.each([
    ['邮件密码', mailAccountSchema, 'password'],
    ['短信账号', smsChannelSchema, 'apiKey'],
    ['社交密钥', socialClientSchema, 'clientSecret'],
  ] as const)(
    '%s：新增必填，编辑省略凭据，重开新增恢复必填',
    async (_, factory, fieldName) => {
      const { api, errors } = await mountForm(false, () =>
        factory().filter((field) =>
          [fieldName, 'id'].includes(field.fieldName),
        ),
      );
      expect((await api.validate()).valid).toBe(false);
      await api.setValues({ id: '9007199254740993' });
      await vi.waitFor(async () =>
        expect((await api.validate()).valid).toBe(true),
      );
      await api.setValues({ [fieldName]: 'replacement-secret' });
      expect((await api.validate()).valid).toBe(true);
      await api.reset();
      await vi.waitFor(async () =>
        expect((await api.validate()).valid).toBe(false),
      );
      expect(errors).toEqual([]);
    },
  );
  it('新开用户表单主动加载字典，性别与备注可见且保存真实值', async () => {
    const { container, api, loader, errors } = await mountForm();
    await vi.waitFor(
      () => {
        expect(errors).toEqual([]);
        expect(container.querySelector('textarea')).not.toBeNull();
        expect(container.querySelectorAll('input[type="radio"]')).toHaveLength(
          2,
        );
      },
      { timeout: 5000 },
    );
    expect(loader).toHaveBeenCalledOnce();
    const remark = container.querySelector('textarea')!;
    remark.value = '测试备注';
    remark.dispatchEvent(new Event('input', { bubbles: true }));
    container
      .querySelectorAll<HTMLInputElement>('input[type="radio"]')[1]!
      .click();
    await nextTick();
    expect(await api.getValues()).toMatchObject({ remark: '测试备注', sex: 2 });
    expect(errors).toEqual([]);
  });
  it('部门树显示层级文字，选择与回填保留雪花字符串 ID', async () => {
    const { container, api, errors } = await mountForm();
    await vi.waitFor(
      () => {
        expect(errors).toEqual([]);
        expect(
          [...container.querySelectorAll('.el-select__placeholder')].some(
            (e) => e.textContent === '请选择归属部门',
          ),
        ).toBe(true);
      },
      { timeout: 5000 },
    );
    [...container.querySelectorAll<HTMLElement>('.el-select__placeholder')]
      .find((e) => e.textContent === '请选择归属部门')!
      .click();
    await vi.waitFor(() =>
      expect(
        [...document.querySelectorAll('.el-tree [role="option"]')].some(
          (e) => e.textContent === '技术部',
        ),
      ).toBe(true),
    );
    const label = [
      ...document.querySelectorAll<HTMLElement>('.el-tree [role="option"]'),
    ].find((e) => e.textContent === '技术部')!;
    label.click();
    await nextTick();
    expect(await api.getValues()).toMatchObject({ deptId: '9007199254740994' });
    await api.setValues({ deptId: '9007199254740993' });
    await nextTick();
    expect(container.textContent).toContain('测试公司');
    expect(errors).toEqual([]);
  });
  it('查询表单包含可交互的起止时间，更新值不会丢失', async () => {
    const { container, api, errors } = await mountForm(true);
    await vi.waitFor(() =>
      expect(container.querySelectorAll('.el-range-input')).toHaveLength(2),
    );
    const range = [new Date(2026, 8, 1), new Date(2026, 8, 23, 23, 59, 59)];
    await api.setValues({ createTime: range });
    await nextTick();
    expect(
      container.querySelector<HTMLInputElement>('.el-range-input')!.value,
    ).toContain('2026-09-01');
    expect((await api.getValues()).createTime).toEqual(range);
    expect(errors).toEqual([]);
  });
  it('配置编码在异步回填 ID 后禁用，清除 ID 后恢复可编辑', async () => {
    const { api, container } = await mountForm(false, () =>
      configSchema().filter((field) =>
        ['code', 'id'].includes(field.fieldName),
      ),
    );
    const input = () =>
      container.querySelector<HTMLInputElement>(
        'input[placeholder="请输入配置类型编码"]',
      )!;
    await vi.waitFor(() => expect(input()).not.toBeNull());
    expect(input().disabled).toBe(false);
    await api.setValues({ id: '9007199254740993', code: 'sample' });
    await vi.waitFor(() => expect(input().disabled).toBe(true));
    await api.setValues({ id: undefined });
    await vi.waitFor(() => expect(input().disabled).toBe(false));
  });
  it('部门编辑的上级选项排除自身及整个子树', async () => {
    const { api, container } = await mountForm(false, () =>
      deptSchema().filter((field) =>
        ['id', 'parentId'].includes(field.fieldName),
      ),
    );
    await api.setValues({ id: '9007199254740993' });
    await vi.waitFor(() =>
      expect(container.querySelector('.el-select__wrapper')).not.toBeNull(),
    );
    container.querySelector<HTMLElement>('.el-select__wrapper')!.click();
    await vi.waitFor(() =>
      expect(document.querySelector('.el-tree')?.textContent).toContain(
        '顶级部门',
      ),
    );
    expect(document.querySelector('.el-tree')?.textContent).not.toContain(
      '技术部',
    );
    expect(document.querySelector('.el-tree')?.textContent).not.toContain(
      '测试公司',
    );
  });
});
