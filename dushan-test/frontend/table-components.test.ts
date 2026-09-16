import { createApp, h, nextTick, ref } from 'vue';

import { useAccessStore } from '@vben/stores';
import { RequestClient } from '@vben/request';

import { createPinia } from 'pinia';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { BusinessError } from '../../dushan-admin-frontend/apps/web-ele/src/api/business-error';
import { nativeResponseInterceptor } from '../../dushan-admin-frontend/apps/web-ele/src/api/response';
import { useDescription } from '../../dushan-admin-frontend/apps/web-ele/src/components/description/use-description';
import ExportTable from '../../dushan-admin-frontend/apps/web-ele/src/components/export-table/export-table.vue';
import {
  exportColumns,
  ExportTask,
} from '../../dushan-admin-frontend/apps/web-ele/src/components/export-table/task';
import IFrame from '../../dushan-admin-frontend/apps/web-ele/src/components/iframe.vue';
import TableAction from '../../dushan-admin-frontend/apps/web-ele/src/components/table-action/table-action.vue';
import { canShowAction } from '../../dushan-admin-frontend/apps/web-ele/src/components/table-action/types';
import { VxeGridApi } from '../../dushan-admin-frontend/packages/effects/plugins/src/vxe-table/api';

const disposers: Array<() => void> = [];
afterEach(() => {
  for (const dispose of disposers.splice(0)) dispose();
  vi.restoreAllMocks();
});
function mount(render: () => ReturnType<typeof h>) {
  const pinia = createPinia();
  const access = useAccessStore(pinia);
  const container = document.createElement('div');
  document.body.append(container);
  const app = createApp({ render });
  app.use(pinia);
  const errors: unknown[] = [];
  app.config.errorHandler = (error) => errors.push(error);
  app.mount(container);
  disposers.push(() => {
    app.unmount();
    container.remove();
  });
  return { container, access, errors };
}
describe('表格展示交互', () => {
  it('更多菜单实际触发动作，在途动作不重复执行', async () => {
    const pending = Promise.withResolvers<undefined>();
    const onClick = vi.fn(() => pending.promise);
    const { container } = mount(() =>
      h(TableAction, { dropDownActions: [{ label: '更多操作', onClick }] }),
    );
    container.querySelector('button')!.click();
    await vi.waitFor(() =>
      expect(document.querySelector('.el-dropdown-menu button')).not.toBeNull(),
    );
    const button = document.querySelector<HTMLButtonElement>(
      '.el-dropdown-menu button',
    )!;
    button.click();
    button.click();
    expect(onClick).toHaveBeenCalledOnce();
    pending.resolve(undefined);
    await nextTick();
  });
  it('按权限和ifShow过滤，真实确认框确认前不执行业务回调', async () => {
    const clicked = vi.fn();
    const confirmed = vi.fn(async () => undefined);
    const actions = [
      {
        label: '删除',
        auth: ['delete'],
        onClick: clicked,
        popConfirm: {
          title: '确认删除',
          confirm: confirmed,
          okText: '确认执行',
        },
      },
      { label: '无权限', auth: ['other'], onClick: clicked },
    ];
    const { container, access, errors } = mount(() =>
      h(TableAction, { actions }),
    );
    expect(container.textContent).not.toContain('删除');
    access.setAccessCodes(['delete']);
    await nextTick();
    expect(container.textContent).toContain('删除');
    expect(container.textContent).not.toContain('无权限');
    container.querySelector('button')!.click();
    await vi.waitFor(() =>
      expect(document.querySelector('.el-popconfirm__action')).not.toBeNull(),
    );
    expect(clicked).not.toHaveBeenCalled();
    expect(confirmed).not.toHaveBeenCalled();
    const button = [
      ...document.querySelectorAll<HTMLButtonElement>(
        '.el-popconfirm__action button',
      ),
    ].find((item) => item.textContent?.includes('确认执行'))!;
    button.click();
    await vi.waitFor(() => expect(confirmed).toHaveBeenCalledOnce());
    expect(clicked).not.toHaveBeenCalled();
    expect(errors).toEqual([]);
    expect(canShowAction({ ifShow: false }, () => true)).toBe(false);
    expect(canShowAction({ ifShow: () => false }, () => true)).toBe(false);
  });
  it('在确认前撤权，已经出现的确认按钮也不能执行', async () => {
    const confirmed = vi.fn();
    const { container, access } = mount(() =>
      h(TableAction, {
        actions: [
          {
            label: '删除',
            auth: ['delete'],
            popConfirm: { title: '确认', confirm: confirmed },
          },
        ],
      }),
    );
    access.setAccessCodes(['delete']);
    await nextTick();
    container.querySelector('button')!.click();
    await vi.waitFor(() =>
      expect(
        document.querySelector('.el-popconfirm__action .el-button--primary'),
      ).not.toBeNull(),
    );
    const button = document.querySelector<HTMLButtonElement>(
      '.el-popconfirm__action .el-button--primary',
    )!;
    access.setAccessCodes([]);
    button.click();
    await nextTick();
    expect(confirmed).not.toHaveBeenCalled();
  });
  it('详情Ref更新和API更新不丢失0/false，空值用破折号', async () => {
    const data = ref({ count: 0, enabled: false, empty: '', hidden: true });
    const [Description, api] = useDescription({
      data,
      schema: [
        { field: 'count', label: '数量' },
        { field: 'enabled', label: '启用' },
        { field: 'empty', label: '空值' },
        {
          label: '隐藏',
          hidden: (value) => value.hidden === true,
          content: 'secret',
        },
      ],
    });
    const { container, errors } = mount(() => h(Description));
    expect(container.textContent).toContain('0');
    expect(container.textContent).toContain('false');
    expect(container.textContent).toContain('—');
    expect(container.textContent).not.toContain('secret');
    data.value.count = 2;
    await nextTick();
    expect(container.textContent).toContain('2');
    api.setState({ data: { count: 3, enabled: false } });
    await nextTick();
    expect(container.textContent).toContain('3');
    expect(errors).toEqual([]);
  });
  it('NEW工具栏API切换搜索及刷新代理，不需要额外connect hook', async () => {
    const api = new VxeGridApi({
      gridOptions: {
        toolbarConfig: {
          search: true,
          refresh: true,
          custom: true,
          zoom: true,
        },
      },
    });
    const commitProxy = vi.fn(async () => undefined);
    api.grid = { commitProxy } as typeof api.grid;
    expect(api.toggleSearchForm(false)).toBe(false);
    expect(api.toggleSearchForm()).toBe(true);
    await api.reload({ status: 0 });
    expect(commitProxy).toHaveBeenCalledWith('reload', { status: 0 });
  });
  it('iframe空态和危险地址；错误不会渲染不可信协议', () => {
    const empty = mount(() => h(IFrame, { src: '', height: 300 }));
    expect(empty.container.querySelector('iframe')).toBeNull();
    expect(empty.container.firstElementChild?.getAttribute('style')).toContain(
      '300px',
    );
    const unsafe = mount(() => h(IFrame, { src: 'javascript:alert(1)' }));
    expect(unsafe.errors[0]).toBeInstanceOf(TypeError);
    expect(unsafe.container.querySelector('iframe')).toBeNull();
  });
  it('iframe源变化重置加载状态，重载替换节点且发出事件', async () => {
    vi.spyOn(HTMLIFrameElement.prototype, 'src', 'set').mockImplementation(
      () => undefined,
    );
    const src = ref('https://example.test/docs');
    const loaded = vi.fn();
    const reloaded = vi.fn();
    const api = ref<{ reload: () => void }>();
    const { container } = mount(() =>
      h(IFrame, {
        ref: api,
        src: src.value,
        onLoad: loaded,
        onReload: reloaded,
      }),
    );
    const first = container.querySelector('iframe')!;
    expect(container.querySelector('[role="status"]')).not.toBeNull();
    first.dispatchEvent(new Event('load'));
    await nextTick();
    expect(loaded).toHaveBeenCalledOnce();
    expect(container.querySelector('[role="status"]')).toBeNull();
    api.value!.reload();
    await nextTick();
    expect(reloaded).toHaveBeenCalledOnce();
    expect(container.querySelector('iframe')).not.toBe(first);
    src.value = 'https://example.test/monitor';
    await nextTick();
    expect(container.querySelector('[role="status"]')).not.toBeNull();
  });
});

describe('导出下载边界', () => {
  const columns = [
    { field: 'id', title: 'ID' },
    { field: 'name', title: '名称' },
  ];
  it('关闭真实导出弹窗立即取消请求，不等待关闭动画', async () => {
    const api = ref<{
      setData: (data: unknown) => void;
      open: () => void;
      close: () => void;
    }>();
    const pending = Promise.withResolvers<Blob>();
    const success = vi.fn();
    let signal!: AbortSignal;
    mount(() => h(ExportTable, { ref: api, onSuccess: success }));
    api.value!.setData({
      columns,
      fileName: 'report.xls',
      exportApi: (_params: unknown, next: AbortSignal) => {
        signal = next;
        return pending.promise;
      },
    });
    api.value!.open();
    await vi.waitFor(() =>
      expect(
        document.querySelector('[role="dialog"] .el-button--primary'),
      ).not.toBeNull(),
    );
    document
      .querySelector<HTMLButtonElement>('[role="dialog"] .el-button--primary')!
      .click();
    expect(signal.aborted).toBe(false);
    api.value!.close();
    expect(signal.aborted).toBe(true);
    pending.resolve(new Blob(['file']));
    await nextTick();
    await nextTick();
    expect(success).not.toHaveBeenCalled();
  });
  it('显式文件名与字段，真实下载入口识别业务JSON错误且保留JSON附件', async () => {
    const client = new RequestClient();
    client.addResponseInterceptor(nativeResponseInterceptor());
    const save = vi.fn();
    const task = new ExportTask(save);
    const payload = new Blob(
      [
        JSON.stringify({
          code: 403,
          message: '禁止导出',
          data: null,
          error: null,
        }),
      ],
      { type: 'application/json' },
    );
    let attachment = false;
    const data = {
      columns,
      fileName: 'report.json',
      searchParams: { active: false },
      exportApi: (params: Record<string, unknown>, signal: AbortSignal) =>
        client.download('/export', {
          params,
          signal,
          adapter: async (config) => ({
            config,
            data: payload,
            headers: {
              'content-type': 'application/json',
              ...(attachment
                ? {
                    'content-disposition': 'attachment; filename="report.json"',
                  }
                : {}),
            },
            status: 200,
            statusText: 'OK',
          }),
        }),
    };
    await expect(task.run(data, ['id'])).rejects.toBeInstanceOf(BusinessError);
    expect(save).not.toHaveBeenCalled();
    expect(task.loading).toBe(false);
    attachment = true;
    await task.run(data, ['id']);
    expect(save).toHaveBeenCalledWith({
      fileName: 'report.json',
      source: payload,
    });
  });
  it('取消后晚到的文件不能保存，任务可重试', async () => {
    const pending = Promise.withResolvers<Blob>();
    const save = vi.fn();
    const task = new ExportTask(save);
    let signal!: AbortSignal;
    const data = {
      columns,
      fileName: 'report.xls',
      exportApi: (_params: Record<string, unknown>, value: AbortSignal) => {
        signal = value;
        return pending.promise;
      },
    };
    const run = task.run(data, ['name']);
    task.cancel();
    expect(signal.aborted).toBe(true);
    pending.resolve(new Blob(['file']));
    await expect(run).rejects.toMatchObject({ name: 'AbortError' });
    expect(save).not.toHaveBeenCalled();
    expect(task.loading).toBe(false);
    await task.run({ ...data, exportApi: async () => new Blob(['new']) }, [
      'id',
    ]);
    expect(save).toHaveBeenCalledOnce();
    const canceled = task.run(
      {
        ...data,
        exportApi: async () => {
          throw new Error('transport canceled');
        },
      },
      ['id'],
    );
    task.cancel();
    await expect(canceled).rejects.toMatchObject({ name: 'AbortError' });
  });
  it('移除非字段列并拒绝空选择、未登记字段及空文件名', async () => {
    expect(
      exportColumns([
        ...columns,
        { field: 'select', title: '选择', type: 'checkbox' },
        { field: 'actions', title: '操作', slots: {} },
      ]),
    ).toEqual(columns);
    const data = {
      columns,
      fileName: 'report.xls',
      exportApi: vi.fn(async () => new Blob()),
    };
    const task = new ExportTask(vi.fn());
    await expect(task.run(data, [])).rejects.toThrow();
    await expect(task.run(data, ['unknown'])).rejects.toThrow();
    await expect(task.run({ ...data, fileName: '' }, ['id'])).rejects.toThrow();
    expect(data.exportApi).not.toHaveBeenCalled();
  });
});
