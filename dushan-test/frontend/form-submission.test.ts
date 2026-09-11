import { beforeAll, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick } from 'vue';

import { FormSubmission } from '../../dushan-admin-frontend/apps/web-ele/src/adapter/form-submission';
import { BusinessError } from '../../dushan-admin-frontend/apps/web-ele/src/api/business-error';
import { setupVbenForm } from '../../dushan-admin-frontend/packages/@core/ui-kit/form-ui/src/config';
import { useVbenForm } from '../../dushan-admin-frontend/packages/@core/ui-kit/form-ui/src/use-vben-form';

function failure(fields: { field: string; message: string }[] = []) {
  const body = {
    code: 422,
    message: '请检查填写内容',
    data: null,
    error: fields.length > 0 ? { fields } : null,
  };
  return new BusinessError(body, { url: '/form' });
}

function target() {
  const values = { mobile: 'old', age: 1 };
  const errors = new Map<string, string>();
  const form = {
    isMounted: true,
    form: {},
    getRawValues: async () => ({ ...values }),
    getFieldComponentRef: (name: string) =>
      ['mobile', 'age'].includes(name) ? {} : undefined,
    setFieldError: vi.fn(async (name: string, message?: string) => {
      if (message) errors.set(name, message);
      else errors.delete(name);
    }),
    scrollToFirstError: vi.fn(),
  };
  const notify = vi.fn();
  return {
    form,
    values,
    errors,
    notify,
    submission: new FormSubmission(form, notify),
  };
}

beforeAll(() => {
  setupVbenForm({ config: {} });
});

describe('当前表单的服务端字段错误', () => {
  it('只给当前表单映射字段，重复明细合并且默认不弹全局通知', async () => {
    const a = target(),
      b = target();
    const result = await a.submission.submit(async (config) => {
      expect(config).toEqual({ errorMessageMode: 'form' });
      throw failure([
        { field: 'mobile', message: '手机号错误' },
        { field: 'mobile', message: '手机号错误' },
        { field: 'age', message: '年龄错误' },
      ]);
    });
    expect(result.status).toBe('error');
    expect(a.errors).toEqual(
      new Map([
        ['mobile', '手机号错误'],
        ['age', '年龄错误'],
      ]),
    );
    expect(a.form.scrollToFirstError).toHaveBeenCalledWith('mobile');
    expect(a.notify).not.toHaveBeenCalled();
    expect(b.errors.size).toBe(0);
  });

  it('不存在的字段只给出一条整体提示，允许显式开启摘要', async () => {
    const a = target();
    await a.submission.submit(async () => {
      throw failure([{ field: 'missing', message: '不可见字段错误' }]);
    });
    expect(a.notify).toHaveBeenCalledTimes(1);
    expect(a.notify.mock.calls[0][0]).toContain('不可见字段错误');
    a.notify.mockClear();
    await a.submission.submit(
      async () => {
        throw failure([{ field: 'mobile', message: '手机号错误' }]);
      },
      { showSummary: true },
    );
    expect(a.notify).toHaveBeenCalledOnce();
  });

  it('重新提交会清除旧服务端错误，成功结果明确返回数据', async () => {
    const a = target();
    await a.submission.submit(async () => {
      throw failure([{ field: 'mobile', message: '错误' }]);
    });
    expect(await a.submission.submit(async () => ({ saved: true }))).toEqual({
      status: 'success',
      data: { saved: true },
    });
    expect(a.errors.size).toBe(0);
  });

  it('用户修改字段后，旧响应不覆盖该字段的新输入', async () => {
    const a = target();
    await a.submission.submit(async () => {
      a.values.mobile = 'new';
      throw failure([{ field: 'mobile', message: '旧值错误' }]);
    });
    expect(a.errors.size).toBe(0);
    expect(a.notify).not.toHaveBeenCalled();
  });

  it.each(['closed', 'reopened'])('表单%s后不写入迟到错误', async (state) => {
    const a = target();
    const result = await a.submission.submit(async () => {
      if (state === 'closed') a.form.isMounted = false;
      else a.form.form = {};
      throw failure([{ field: 'mobile', message: '旧提交错误' }]);
    });
    expect(result.status).toBe('stale');
    expect(a.errors.size).toBe(0);
    expect(a.notify).not.toHaveBeenCalled();
  });

  it('较早的并发提交不能覆盖新一次提交结果', async () => {
    const a = target();
    let rejectFirst!: (reason: unknown) => void;
    let started!: () => void;
    const ready = new Promise<void>((resolve) => {
      started = resolve;
    });
    const first = a.submission.submit(() => {
      started();
      return new Promise((_, reject) => {
        rejectFirst = reject;
      });
    });
    await ready;
    const latest = await a.submission.submit(async () => true);
    expect(latest.status).toBe('success');
    rejectFirst(failure([{ field: 'mobile', message: '旧错误' }]));
    const previous = await first;
    expect(previous.status).toBe('stale');
    expect(a.errors.size).toBe(0);
  });

  it('网络或程序异常继续传播，普通业务失败只提示一次', async () => {
    const a = target();
    const error = new Error('network');
    await expect(
      a.submission.submit(async () => {
        throw error;
      }),
    ).rejects.toBe(error);
    await a.submission.submit(async () => {
      throw failure();
    });
    expect(a.notify).toHaveBeenCalledExactlyOnceWith('请检查填写内容');
  });

  it('真实Vben表单显示错误文字和错误样式，修改输入后清除', async () => {
    const Input = defineComponent({
      inheritAttrs: false,
      setup(_, { attrs, emit }) {
        return () =>
          h('input', {
            ...attrs,
            value: attrs.modelValue ?? '',
            onInput: (event: Event) =>
              emit(
                'update:modelValue',
                (event.target as HTMLInputElement).value,
              ),
          });
      },
    });
    const [Form, api] = useVbenForm({
      schema: [{ component: Input, fieldName: 'mobile', label: '手机号' }],
      showDefaultActions: false,
    });
    const host = document.createElement('div');
    document.body.append(host);
    const app = createApp({ render: () => h(Form) });
    app.mount(host);
    try {
      await api.getRawValues();
      const notification = vi.fn();
      const submission = new FormSubmission(api, notification);
      await submission.submit(async () => {
        throw failure([{ field: 'mobile', message: '手机号格式不正确' }]);
      });
      await nextTick();
      expect(host.textContent).toContain('手机号格式不正确');
      expect(host.querySelector('input')?.className).toContain(
        'border-destructive',
      );
      const input = host.querySelector('input');
      if (!input) throw new Error('找不到手机号输入框');
      input.value = '13812348000';
      input.dispatchEvent(new Event('input', { bubbles: true }));
      await vi.waitFor(() =>
        expect(host.textContent).not.toContain('手机号格式不正确'),
      );
      expect(notification).not.toHaveBeenCalled();
    } finally {
      app.unmount();
      host.remove();
    }
  });
});
