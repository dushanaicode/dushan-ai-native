import { createApp, h, nextTick, ref } from 'vue';

import { afterEach, expect, it, vi } from 'vitest';

import CronTab from '../../dushan-admin-frontend/apps/web-ele/src/components/cron-tab/cron-tab.vue';
import RichTextarea from '../../dushan-admin-frontend/apps/web-ele/src/components/rich-textarea.vue';
import StepWizard from '../../dushan-admin-frontend/apps/web-ele/src/components/step-wizard.vue';
import ImageUpload from '../../dushan-admin-frontend/apps/web-ele/src/components/upload/image-upload.vue';

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
  let active = true;
  const dispose = () => {
    if (active) {
      active = false;
      app.unmount();
      container.remove();
    }
  };
  disposers.push(dispose);
  return { container, errors, dispose };
}
const descriptor = {
  id: '18446744073709551615',
  name: 'saved.png',
  size: 2,
  mediaType: 'image/png',
};

it('cron不截断六段原输入，合法表达式打开确认保持原值', async () => {
  const value = ref('0 0 0 * * *');
  const disabled = ref(false);
  const changed = vi.fn();
  const { container, errors } = mount(() =>
    h(CronTab, {
      disabled: disabled.value,
      modelValue: value.value,
      'onUpdate:modelValue': (next) => {
        value.value = next;
      },
      onChange: changed,
    }),
  );
  container
    .querySelector<HTMLButtonElement>('.el-input-group__append button')!
    .click();
  await nextTick();
  expect(value.value).toBe('0 0 0 * * *');
  expect(changed).not.toHaveBeenCalled();
  expect(container.querySelector('[role="alert"]')).not.toBeNull();
  value.value = '*/10 0 * * 1';
  await nextTick();
  container
    .querySelector<HTMLButtonElement>('.el-input-group__append button')!
    .click();
  await vi.waitFor(() =>
    expect(document.querySelector('[role="dialog"] code')?.textContent).toBe(
      value.value,
    ),
  );
  const confirm = document.querySelector<HTMLButtonElement>(
    '[role="dialog"] .el-button--primary',
  )!;
  disabled.value = true;
  await nextTick();
  confirm.click();
  expect(changed).not.toHaveBeenCalled();
  disabled.value = false;
  await nextTick();
  container
    .querySelector<HTMLButtonElement>('.el-input-group__append button')!
    .click();
  await nextTick();
  document
    .querySelector<HTMLButtonElement>('[role="dialog"] .el-button--primary')!
    .click();
  await nextTick();
  expect(changed).toHaveBeenCalledWith('*/10 0 * * 1');
  expect(errors).toEqual([]);
});
it('步骤切换保留插槽实例，loading禁止跳步，事件与受控值一致', async () => {
  const api = ref<{ nextStep: () => void; prevStep: () => void }>();
  const current = ref(0);
  const loading = ref(false);
  const next = vi.fn();
  const { container } = mount(() =>
    h(
      StepWizard,
      {
        ref: api,
        steps: [{ title: 'A' }, { title: 'B' }, { title: 'C', disabled: true }],
        current: current.value,
        loading: loading.value,
        'onUpdate:current': (value) => {
          current.value = value;
        },
        onNext: next,
      },
      {
        'step-0': () => h('input', { id: 'kept-input' }),
        'step-1': () => h('p', 'Second'),
      },
    ),
  );
  const input = container.querySelector<HTMLInputElement>('#kept-input')!;
  input.value = '保留内容';
  api.value!.nextStep();
  await nextTick();
  expect(current.value).toBe(1);
  expect(next).toHaveBeenCalledWith(0, 1);
  loading.value = true;
  await nextTick();
  api.value!.prevStep();
  expect(current.value).toBe(1);
  loading.value = false;
  await nextTick();
  api.value!.nextStep();
  expect(current.value).toBe(1);
  api.value!.prevStep();
  await nextTick();
  expect(container.querySelector('#kept-input')).toBe(input);
  expect(input.value).toBe('保留内容');
});
it('ImageUpload实际表单事件只返回ID，默认展示已上传项；同值重置可显式取消', async () => {
  vi.spyOn(HTMLImageElement.prototype, 'src', 'set').mockImplementation(
    () => undefined,
  );
  const value = ref<string>();
  const api = ref<{ cancel: () => void }>();
  const updates = vi.fn((next: string) => {
    value.value = next;
  });
  const pending = Promise.withResolvers<typeof descriptor>();
  const upload = vi.fn(() => pending.promise);
  const resolve = vi.fn(async (ids: string[]) =>
    ids.map((id) => ({
      ...descriptor,
      id,
      url: '/files/access?ticket=temporary',
    })),
  );
  const ports = { upload, resolve };
  const { container, errors } = mount(() =>
    h(ImageUpload, {
      ref: api,
      modelValue: value.value,
      ports,
      'onUpdate:modelValue': updates,
    }),
  );
  const input =
    container.querySelector<HTMLInputElement>('input[type="file"]')!;
  Object.defineProperty(input, 'files', {
    configurable: true,
    value: [new File(['ok'], 'input.png', { type: 'image/png' })],
  });
  input.dispatchEvent(new Event('change', { bubbles: true }));
  expect(upload).toHaveBeenCalledOnce();
  pending.resolve(descriptor);
  await vi.waitFor(() => expect(value.value).toBe(descriptor.id));
  await vi.waitFor(() => expect(container.textContent).toContain('saved.png'));
  expect(JSON.stringify(updates.mock.calls)).not.toContain('ticket');
  const remove = [
    ...container.querySelectorAll<HTMLButtonElement>('button'),
  ].find((button) => button.textContent?.includes('utils.upload.remove'))!;
  remove.click();
  await nextTick();
  expect(value.value).toBeUndefined();
  const late = Promise.withResolvers<typeof descriptor>();
  upload.mockReturnValueOnce(late.promise);
  input.dispatchEvent(new Event('change', { bubbles: true }));
  api.value!.cancel();
  late.resolve(descriptor);
  await nextTick();
  await nextTick();
  expect(value.value).toBeUndefined();
  expect(errors).toEqual([]);
});

function pasteImage(editor: Element) {
  const file = new File(['ok'], 'image.png', { type: 'image/png' });
  const event = new Event('paste', { bubbles: true, cancelable: true });
  Object.defineProperty(event, 'clipboardData', {
    value: {
      getData: () => '',
      types: ['Files'],
      files: [file],
      items: [{ type: 'image/png', getAsFile: () => file }],
    },
  });
  editor.dispatchEvent(event);
}
function preventImageNetwork() {
  vi.spyOn(HTMLImageElement.prototype, 'src', 'set').mockImplementation(
    () => undefined,
  );
  vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:pending-image');
  return vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined);
}
it('真实Tiptap粘贴图片调用端口，blob占位不会进入表单值；完成后输出持久HTML', async () => {
  const revoke = preventImageNetwork();
  const value = ref('<p>正文</p>');
  const pending = Promise.withResolvers<string>();
  const onPending = vi.fn();
  const upload = vi.fn(() => pending.promise);
  const updates = vi.fn((next: string) => {
    value.value = next;
  });
  const { container, errors } = mount(() =>
    h(RichTextarea, {
      modelValue: value.value,
      'onUpdate:modelValue': updates,
      imageUpload: { upload },
      toolbar: false,
      previewable: false,
      onPending,
    }),
  );
  await vi.waitFor(() =>
    expect(container.querySelector('.tiptap')).not.toBeNull(),
  );
  pasteImage(container.querySelector('.tiptap')!);
  await vi.waitFor(() => expect(upload).toHaveBeenCalledOnce());
  expect(onPending).toHaveBeenCalledWith(true);
  expect(value.value).toBe('<p>正文</p>');
  pending.resolve('/files/permanent-image');
  await vi.waitFor(() =>
    expect(value.value).toContain('src="/files/permanent-image"'),
  );
  expect(JSON.stringify(updates.mock.calls)).not.toContain('blob:');
  expect(onPending).toHaveBeenLastCalledWith(false);
  expect(revoke).toHaveBeenCalledWith('blob:pending-image');
  expect(errors).toEqual([]);
});
it('取消富文本上传及时移除占位，忽略晚到URL；外部HTML更新仍回显', async () => {
  preventImageNetwork();
  const value = ref('<p>正文</p>');
  const pending = Promise.withResolvers<string>();
  const api = ref<{ cancelUploads: () => void; pending: boolean }>();
  const onError = vi.fn();
  let signal!: AbortSignal;
  const { container, dispose, errors } = mount(() =>
    h(RichTextarea, {
      ref: api,
      modelValue: value.value,
      'onUpdate:modelValue': (next) => {
        value.value = next;
      },
      imageUpload: {
        upload: (_file, next) => {
          signal = next;
          return pending.promise;
        },
      },
      toolbar: false,
      previewable: false,
      onError,
    }),
  );
  await vi.waitFor(() =>
    expect(container.querySelector('.tiptap')).not.toBeNull(),
  );
  pasteImage(container.querySelector('.tiptap')!);
  await vi.waitFor(() => expect(api.value!.pending).toBe(true));
  api.value!.cancelUploads();
  expect(signal.aborted).toBe(true);
  await vi.waitFor(() =>
    expect(container.querySelector('.tiptap img')).toBeNull(),
  );
  pending.resolve('/files/late-image');
  await nextTick();
  expect(value.value).not.toContain('late-image');
  expect(onError).not.toHaveBeenCalled();
  value.value = '<p>新的正文</p>';
  await vi.waitFor(() =>
    expect(container.querySelector('.tiptap p')?.textContent).toBe('新的正文'),
  );
  dispose();
  expect(errors).toEqual([]);
});
