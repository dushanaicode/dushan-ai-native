import { afterEach, describe, expect, it, vi } from 'vitest';
import { computed, createApp, h, nextTick, ref } from 'vue';

import DictTag from '../../dushan-admin-frontend/apps/web-ele/src/components/dict-tag.vue';
import TagEditor from '../../dushan-admin-frontend/apps/web-ele/src/components/tag-editor.vue';
import { tagPresentation } from '../../dushan-admin-frontend/apps/web-ele/src/components/tag-style';
import { provideDictionary } from '../../dushan-admin-frontend/apps/web-ele/src/services/dictionary/context';
import {
  convertDictionaryValue,
  DictionaryRuntime,
} from '../../dushan-admin-frontend/apps/web-ele/src/services/dictionary/runtime';
import type {
  DictionaryEntry,
  TagStyle,
} from '../../dushan-admin-frontend/apps/web-ele/src/services/dictionary/types';
import { SessionCoordinator } from '../../dushan-admin-frontend/apps/web-ele/src/services/session/coordinator';

vi.mock('@vben/locales', () => ({ $t: (key: string) => key }));

const cleanup: Array<() => void> = [];
afterEach(() => {
  for (const dispose of cleanup.splice(0)) dispose();
});

function setup() {
  let snapshot = { generation: 'one', token: 'token' as null | string };
  const session = new SessionCoordinator({
    read: () => snapshot,
    write: (next) => {
      snapshot = { ...next };
    },
    expire: async () => {},
    refresh: async () => 'new',
    lock: (operation) => operation(),
    subscribe: () => () => {},
  });
  const locale = ref('zh-CN');
  const entries: DictionaryEntry[] = [
    { dictType: 'status', value: '0', label: '关闭', colorType: null },
    { dictType: 'status', value: '1', label: '开启', permission: 'edit' },
    { dictType: 'boolean', value: 'false', label: '否' },
    { dictType: 'boolean', value: 'true', label: '是' },
  ];
  const loader = vi.fn(
    async (_signal: AbortSignal, _locale: string): Promise<unknown> => entries,
  );
  const dictionary = new DictionaryRuntime({ loader, locale, session });
  cleanup.push(() => {
    dictionary.dispose();
    session.dispose();
  });
  return { dictionary, entries, loader, locale, session };
}

describe('字典单一来源与失效', () => {
  it('外部数据按明确结构校验，不接收数值编码或字符串 JSON 样式', async () => {
    const { dictionary, loader, entries } = setup();
    for (const entry of [
      { ...entries[0], value: 0 },
      { ...entries[0], tagStyle: '{"variant":"solid"}' },
      { ...entries[0], extra: 'unsupported' },
    ]) {
      loader.mockResolvedValueOnce([entry]);
      await expect(dictionary.load()).rejects.toThrow();
      expect(dictionary.status).toBe('error');
    }
  });

  it('并发 ensure 共享 Promise，按类型分组，0/false 查询与转换保留', async () => {
    const { dictionary, loader } = setup();
    const operation = dictionary.ensure();
    expect(dictionary.ensure()).toBe(operation);
    await operation;
    expect(loader).toHaveBeenCalledOnce();
    expect(dictionary.status).toBe('ready');
    expect(dictionary.getDictLabel('status', 0)).toBe('关闭');
    expect(dictionary.getDictLabel('boolean', false)).toBe('否');
    expect(
      dictionary.getDictOptions('status', 'number').map((item) => item.value),
    ).toEqual([0, 1]);
    expect(
      dictionary.getDictOptions('boolean', 'boolean').map((item) => item.value),
    ).toEqual([false, true]);
    expect(dictionary.getDictOptions('missing', 'string')).toEqual([]);
  });

  it('失败不缓存，显式重试成功，重复值明确拒绝', async () => {
    const { dictionary, loader, entries } = setup();
    const failure = new Error('字典读取失败');
    loader.mockRejectedValueOnce(failure);
    await expect(dictionary.ensure()).rejects.toBe(failure);
    expect(dictionary.status).toBe('error');
    expect(dictionary.error).toBe(failure);
    await dictionary.ensure();
    expect(loader).toHaveBeenCalledTimes(2);
    loader.mockResolvedValue([entries[0]!, entries[0]!]);
    await expect(dictionary.load()).rejects.toThrow('字典值重复');
  });

  it('显式失效与语言变化更新派生选项，调用方不能修改缓存快照', async () => {
    const { dictionary, entries, loader, locale } = setup();
    const options = computed(() =>
      dictionary.getDictOptions('status', 'string'),
    );
    await dictionary.ensure();
    entries[0]!.label = '禁用';
    expect(options.value[0]?.label).toBe('关闭');
    dictionary.invalidate();
    expect(options.value).toEqual([]);
    await dictionary.ensure();
    expect(options.value[0]?.label).toBe('禁用');
    locale.value = 'en-US';
    expect(dictionary.status).toBe('idle');
    await dictionary.ensure();
    expect(loader).toHaveBeenLastCalledWith(expect.any(AbortSignal), 'en-US');
    expect(() => {
      (dictionary.getDictData('status', 0) as DictionaryEntry).label =
        'changed';
    }).toThrow();
  });

  it('换会话丢弃迟到结果；协调器销毁也关闭字典与监听', async () => {
    const { dictionary, session, loader, entries, locale } = setup();
    const pending = Promise.withResolvers<DictionaryEntry[]>();
    loader.mockReturnValue(pending.promise);
    const operation = Promise.allSettled([dictionary.ensure()]);
    await vi.waitFor(() => expect(loader).toHaveBeenCalledOnce());
    session.replace('other');
    pending.resolve(entries);
    expect((await operation)[0]?.status).toBe('rejected');
    expect(dictionary.getDictOptions('status', 'string')).toEqual([]);
    session.dispose();
    const version = dictionary.version;
    locale.value = 'new-locale';
    expect(dictionary.version).toBe(version);
    await expect(dictionary.ensure()).rejects.toMatchObject({
      name: 'InvalidStateError',
    });
  });

  it('旧加载的 finally 不清掉新加载；已取消但尚未执行的 loader 不启动', async () => {
    const { dictionary, loader, entries } = setup();
    const cancelled = Promise.allSettled([dictionary.ensure()]);
    dictionary.invalidate();
    await cancelled;
    expect(loader).not.toHaveBeenCalled();
    const old = Promise.withResolvers<DictionaryEntry[]>();
    const current = Promise.withResolvers<DictionaryEntry[]>();
    loader
      .mockReturnValueOnce(old.promise)
      .mockReturnValueOnce(current.promise);
    const oldResult = Promise.allSettled([dictionary.ensure()]);
    await vi.waitFor(() => expect(loader).toHaveBeenCalledOnce());
    dictionary.invalidate();
    const active = dictionary.ensure();
    old.resolve(entries);
    await oldResult;
    expect(dictionary.ensure()).toBe(active);
    current.resolve(entries);
    await active;
  });

  it('类型转换不截断或猜测，标识字符串保持原样', () => {
    expect(convertDictionaryValue('9223372036854775807', 'string')).toBe(
      '9223372036854775807',
    );
    for (const value of ['1x', '1.2', '', '9223372036854775807'])
      expect(() => convertDictionaryValue(value, 'number')).toThrow();
    expect(() => convertDictionaryValue('anything', 'boolean')).toThrow();
  });
});

describe('字典展示与标签编辑', () => {
  it('加载失败显示重试，保留原始错误事件，重试成功后显示标签', async () => {
    const { dictionary, loader } = setup();
    const failure = new Error('加载失败');
    loader.mockRejectedValueOnce(failure);
    const errors: unknown[] = [];
    const element = document.createElement('div');
    const app = createApp(() =>
      h(DictTag, {
        type: 'status',
        value: 0,
        onError: (error: unknown) => errors.push(error),
      }),
    );
    provideDictionary(app, dictionary);
    app.mount(element);
    cleanup.push(() => app.unmount());
    await vi.waitFor(() =>
      expect(element.textContent).toContain('utils.dictionary.retry'),
    );
    expect(errors).toEqual([failure]);
    element.querySelector<HTMLButtonElement>('button')!.click();
    await vi.waitFor(() => expect(element.textContent).toBe('关闭'));
    expect(loader).toHaveBeenCalledTimes(2);
  });

  it('真实标签组件显示 0/false 与未知值，并在字典失效后更新', async () => {
    const { dictionary, entries } = setup();
    const element = document.createElement('div');
    const app = createApp(() =>
      h('div', [
        h(DictTag, { type: 'status', value: ['', 0, 'unknown'] }),
        h(DictTag, { type: 'boolean', value: false }),
        h(DictTag, { type: 'boolean', value: '' }),
      ]),
    );
    provideDictionary(app, dictionary);
    app.mount(element);
    cleanup.push(() => app.unmount());
    await vi.waitFor(() => expect(element.textContent).toBe('关闭unknown否'));
    expect(element.querySelectorAll('.el-tag')).toHaveLength(3);
    entries[0]!.label = '禁用';
    dictionary.invalidate();
    await vi.waitFor(() => expect(element.textContent).toBe('禁用unknown否'));
  });

  it('标签样式解析不接受无效颜色，浅底自动采用深色文字', () => {
    expect(
      tagPresentation(
        { color: '#ffffff', textColor: '', variant: 'solid' },
        'primary',
        'solid',
      ).color,
    ).toBe('#1f2937');
    expect(
      tagPresentation(
        { color: '#ff0000', textColor: '', variant: 'outline' },
        'primary',
        'solid',
      ).backgroundColor,
    ).toBe('transparent');
    expect(() => tagPresentation(null, 'not-a-color', 'solid')).toThrow();
  });

  it('编辑草稿在确认前不改模型，取消与清除行为明确', async () => {
    const value = ref<null | TagStyle>(null);
    const element = document.createElement('div');
    document.body.append(element);
    const app = createApp(() =>
      h(TagEditor, {
        modelValue: value.value,
        'onUpdate:modelValue': (next) => {
          value.value = next;
        },
      }),
    );
    app.mount(element);
    cleanup.push(() => {
      app.unmount();
      element.remove();
    });
    const click = (text: string, root: ParentNode = document) => {
      const button = [...root.querySelectorAll('button')].find(
        (node) => node.textContent?.trim() === text,
      );
      expect(button).toBeDefined();
      button!.click();
    };
    click('utils.tagEditor.placeholder', element);
    await nextTick();
    document.querySelector<HTMLInputElement>('input[value="outline"]')!.click();
    await nextTick();
    expect(value.value).toBeNull();
    click('utils.tagEditor.cancel');
    await nextTick();
    expect(value.value).toBeNull();
    click('utils.tagEditor.placeholder', element);
    await nextTick();
    document.querySelector<HTMLInputElement>('input[value="outline"]')!.click();
    await nextTick();
    click('utils.tagEditor.apply');
    await nextTick();
    expect(value.value?.variant).toBe('outline');
    click('utils.tagEditor.clear', element);
    await nextTick();
    expect(value.value).toBeNull();
  });
});
