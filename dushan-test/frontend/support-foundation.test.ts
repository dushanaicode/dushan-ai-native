import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, h, nextTick, ref } from 'vue';

import CellSwitch from '../../dushan-admin-frontend/apps/web-ele/src/adapter/cell-switch.vue';
import { formRules } from '../../dushan-admin-frontend/apps/web-ele/src/adapter/form-rules';
import { getRangePickerDefaultProps } from '../../dushan-admin-frontend/apps/web-ele/src/utils/range-picker';
import { toSortingFields } from '../../dushan-admin-frontend/apps/web-ele/src/utils/sorting';

vi.mock('@vben/locales', () => ({ $t: (key: string) => key }));

afterEach(() => vi.useRealTimers());

describe('支撑层数据边界', () => {
  it('排序保持优先级，取消的字段不发送，原始数组不变', () => {
    const sorts = [
      { field: 'createdAt', order: 'desc' as const },
      { field: 'owner.name', order: 'asc' as const },
      { field: 'status', order: null },
    ];
    expect(toSortingFields(sorts)).toEqual(sorts.slice(0, 2));
    expect(sorts).toHaveLength(3);
    expect(toSortingFields([])).toEqual([]);
  });

  it('必填保留 0/false，空数组和空字符串都被拒绝', () => {
    for (const value of [0, false, '0', ['']]) {
      expect(formRules.required(value, [], {})).toBe(true);
      expect(formRules.selectRequired(value, [], {})).toBe(true);
    }
    for (const value of ['', [], undefined, null]) {
      expect(formRules.required(value, [], {})).not.toBe(true);
      expect(formRules.selectRequired(value, [], {})).not.toBe(true);
    }
  });

  it('手机号匹配整个字符串，拒绝数字转换、首尾垃圾和过长内容', () => {
    for (const value of [
      '',
      null,
      undefined,
      '13800138000',
      '+8613800138000',
    ]) {
      expect(formRules.mobile(value, [], {})).toBe(true);
    }
    for (const value of [
      13800138000,
      0,
      false,
      'x13800138000',
      '13800138000x',
      '138001380001',
    ]) {
      expect(formRules.mobile(value, [], {})).not.toBe(true);
    }
  });

  it('范围在点击时计算，覆盖跨年、闰年和日末，不依赖字符串解析插件', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2024, 2, 1, 12));
    const props = getRangePickerDefaultProps();
    const shortcut = (key: string): Date[] => {
      const item = props.shortcuts!.find((entry) => entry.text.endsWith(key))!;
      return (item.value as () => Date[])();
    };
    expect(shortcut('yesterday')).toEqual([
      new Date(2024, 1, 29),
      new Date(2024, 1, 29, 23, 59, 59, 999),
    ]);
    expect(shortcut('last7Days')[0]).toEqual(new Date(2024, 1, 24));
    expect(shortcut('lastMonth')[1]).toEqual(
      new Date(2024, 1, 29, 23, 59, 59, 999),
    );
    vi.setSystemTime(new Date(2025, 0, 1, 12));
    expect(shortcut('yesterday')[0]).toEqual(new Date(2024, 11, 31));
    expect(
      (props.defaultTime as Date[]).every((date) =>
        Number.isFinite(date.getTime()),
      ),
    ).toBe(true);
    expect(props.valueFormat).toBeUndefined();
  });
});

describe('CellSwitch 的实际交互', () => {
  it('明确取消与卸载后的迟到成功都不修改行数据', async () => {
    const cancelled = Promise.withResolvers<false>();
    const pending = Promise.withResolvers<void>();
    const change = vi
      .fn()
      .mockReturnValueOnce(cancelled.promise)
      .mockReturnValueOnce(pending.promise);
    const update = vi.fn();
    const element = document.createElement('div');
    const app = createApp(() =>
      h(CellSwitch, {
        change,
        modelValue: 0,
        'onUpdate:modelValue': update,
      }),
    );
    app.mount(element);
    const button = element.querySelector<HTMLElement>('.el-switch')!;
    const input = element.querySelector<HTMLInputElement>('input')!;
    button.click();
    await nextTick();
    expect(input.disabled).toBe(true);
    cancelled.resolve(false);
    await vi.waitFor(() => expect(input.disabled).toBe(false));
    expect(update).not.toHaveBeenCalled();
    button.click();
    expect(change).toHaveBeenCalledTimes(2);
    await nextTick();
    app.unmount();
    pending.resolve();
    await nextTick();
    expect(update).not.toHaveBeenCalled();
  });

  it('1 开启、0 关闭，等待请求时不改行、不重复调用，失败保留原始错误和原值', async () => {
    const state = ref<0 | 1>(0);
    const first = Promise.withResolvers<void>();
    const failure = new Error('保存失败');
    const change = vi
      .fn()
      .mockReturnValueOnce(first.promise)
      .mockRejectedValueOnce(failure);
    const errors: unknown[] = [];
    const element = document.createElement('div');
    document.body.append(element);
    const app = createApp(() =>
      h(CellSwitch, {
        modelValue: state.value,
        change,
        'onUpdate:modelValue': (value) => {
          state.value = value;
        },
      }),
    );
    app.config.errorHandler = (error) => errors.push(error);
    app.mount(element);
    try {
      const button = element.querySelector<HTMLElement>('.el-switch')!;
      button.click();
      await nextTick();
      button.click();
      expect(change).toHaveBeenCalledExactlyOnceWith(1);
      expect(state.value).toBe(0);
      first.resolve();
      await vi.waitFor(() => expect(state.value).toBe(1));
      button.click();
      await vi.waitFor(() => expect(errors).toEqual([failure]));
      expect(change).toHaveBeenLastCalledWith(0);
      expect(state.value).toBe(1);
      expect(element.querySelector<HTMLInputElement>('input')!.disabled).toBe(
        false,
      );
      expect(element.querySelector<HTMLInputElement>('input')!.checked).toBe(
        true,
      );
    } finally {
      app.unmount();
      element.remove();
    }
  });
});
