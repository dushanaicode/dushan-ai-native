import { createApp, h, nextTick, ref } from 'vue';

import { afterEach, assert, describe, expect, it, vi } from 'vitest';

import VbenTableAction from '../../dushan-admin-frontend/packages/@core/ui-kit/shadcn-ui/src/components/table-action/table-action.vue';

const disposers: Array<() => void> = [];

afterEach(async () => {
  for (const dispose of disposers.splice(0)) dispose();
  await nextTick();
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

function click(button: HTMLButtonElement | null | undefined) {
  assert(button);
  button.click();
}

describe('生成的 Ant Design 页面使用公共表格操作契约', () => {
  it('展示操作文本、执行回调，并随权限变化移除操作', async () => {
    const permitted = ref(true);
    const disabled = ref(false);
    const edit = vi.fn();
    const { container, errors } = mount(() =>
      h(VbenTableAction, {
        actions: [
          {
            text: '编辑',
            variant: 'link',
            ifShow: permitted.value,
            disabled: disabled.value,
            onClick: edit,
          },
        ],
      }),
    );
    expect(container.textContent).toContain('编辑');
    click(container.querySelector('button'));
    expect(edit).toHaveBeenCalledOnce();

    disabled.value = true;
    await nextTick();
    click(container.querySelector('button'));
    expect(edit).toHaveBeenCalledOnce();

    permitted.value = false;
    await nextTick();
    expect(container.querySelector('button')).toBeNull();
    expect(errors).toEqual([]);
  });

  it('删除只在确认后执行，并使用生成页面提供的中文确认文案', async () => {
    const remove = vi.fn();
    const { container, errors } = mount(() =>
      h(VbenTableAction, {
        actions: [
          {
            text: '删除',
            variant: 'link',
            danger: true,
            popConfirm: {
              title: '确认删除记录？',
              okText: '确认',
              cancelText: '取消',
              confirm: remove,
            },
          },
        ],
      }),
    );
    const popupButton = (text: string) =>
      [...document.querySelectorAll<HTMLButtonElement>('button')].find(
        (button) => button.textContent?.trim() === text,
      );

    expect(container.querySelector('button')?.classList).toContain(
      'text-destructive',
    );
    click(container.querySelector('button'));
    await vi.waitFor(() => expect(popupButton('取消')).toBeDefined());
    expect(popupButton('确认')?.classList).toContain('bg-destructive');
    expect(remove).not.toHaveBeenCalled();
    click(popupButton('取消'));
    await vi.waitFor(() => expect(popupButton('取消')).toBeUndefined());
    expect(remove).not.toHaveBeenCalled();

    click(container.querySelector('button'));
    await vi.waitFor(() => expect(popupButton('确认')).toBeDefined());
    click(popupButton('确认'));
    expect(remove).toHaveBeenCalledOnce();
    expect(errors).toEqual([]);
  });
});
