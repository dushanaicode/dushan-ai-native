import type { Component } from 'vue';

import { createApp, defineComponent, h, nextTick, ref } from 'vue';

import { afterEach, describe, expect, it, vi } from 'vitest';

import { useSortable } from '../../dushan-admin-frontend/packages/@core/composables/src/use-sortable';
import Menu from '../../dushan-admin-frontend/packages/@core/ui-kit/menu-ui/src/menu.vue';
import Badge from '../../dushan-admin-frontend/packages/@core/ui-kit/shadcn-ui/src/ui/badge/Badge.vue';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../dushan-admin-frontend/packages/@core/ui-kit/shadcn-ui/src/ui/select';
import Toggle from '../../dushan-admin-frontend/packages/@core/ui-kit/shadcn-ui/src/ui/toggle/Toggle.vue';
import { VbenTiptap } from '../../dushan-admin-frontend/packages/effects/plugins/src/tiptap';

const disposers: Array<() => void> = [];

function mount(component: Component) {
  const container = document.createElement('div');
  document.body.append(container);
  const app = createApp(component);
  const errors: unknown[] = [];
  app.config.errorHandler = (error) => errors.push(error);
  // 菜单的路由边界只提供 href；菜单本身和递归组件使用真实实现。
  app.component(
    'RouterLink',
    defineComponent({
      props: { to: { type: String, required: true }, custom: Boolean },
      setup(props, { slots }) {
        return () => slots.default?.({ href: props.to });
      },
    }),
  );
  disposers.push(() => {
    app.unmount();
    container.remove();
  });
  app.mount(container);
  return { container, errors };
}

afterEach(async () => {
  for (const dispose of disposers.splice(0)) dispose();
  await nextTick();
});

describe('公共组件的实际导入与交互', () => {
  it('拖拽包由消费者解析，真实实例能初始化、排序和销毁', async () => {
    const container = document.createElement('ul');
    container.innerHTML = '<li data-id="a">A</li><li data-id="b">B</li>';
    document.body.append(container);
    const sortable = await useSortable(container).initializeSortable();
    disposers.push(() => {
      sortable.destroy();
      container.remove();
    });
    expect(sortable.toArray()).toEqual(['a', 'b']);
    sortable.sort(['b', 'a']);
    expect(sortable.toArray()).toEqual(['b', 'a']);
  });

  it('编辑器通过 StarterKit 提供文档和下划线，模型更新保留内容', async () => {
    const value = ref('<p><u>带下划线的内容</u></p>');
    const { container, errors } = mount(
      defineComponent({
        setup: () => () =>
          h(VbenTiptap, {
            modelValue: value.value,
            placeholder: '请输入',
            toolbar: false,
            previewable: false,
          }),
      }),
    );
    await vi.waitFor(() => {
      expect(container.querySelector('.tiptap u')?.textContent).toBe(
        '带下划线的内容',
      );
    });
    value.value = '<p>更新后的文档</p>';
    await vi.waitFor(() => {
      expect(container.querySelector('.tiptap')?.textContent).toBe(
        '更新后的文档',
      );
    });
    expect(errors).toEqual([]);
  });

  it('三层递归菜单渲染叶节点并触发选择', async () => {
    const selected = vi.fn();
    const { container, errors } = mount(
      defineComponent({
        setup: () => () =>
          h(Menu, {
            defaultOpeneds: ['/a', '/a/b'],
            menus: [
              {
                name: '一级',
                path: '/a',
                children: [
                  {
                    name: '二级',
                    path: '/a/b',
                    children: [
                      {
                        name: '三级叶节点',
                        path: '/a/b/c',
                        badge: '3',
                        badgeType: 'normal',
                      },
                    ],
                  },
                ],
              },
            ],
            onSelect: selected,
          }),
      }),
    );
    await nextTick();
    expect(errors).toEqual([]);
    const leaf =
      container.querySelector<HTMLAnchorElement>('[role="menuitem"]');
    expect(leaf?.textContent).toContain('三级叶节点');
    expect(leaf?.getAttribute('href')).toBe('/a/b/c');
    leaf?.click();
    await nextTick();
    expect(selected).toHaveBeenCalledWith('/a/b/c', expect.any(Array));
    expect(errors).toEqual([]);
  });

  it('标签样式和 Toggle 状态更新、禁用行为正常', async () => {
    const value = ref(false);
    const disabled = ref(false);
    const { container, errors } = mount(
      defineComponent({
        setup: () => () => [
          h(Badge, { variant: 'destructive' }, () => '状态标签'),
          h(
            Toggle,
            {
              disabled: disabled.value,
              modelValue: value.value,
              variant: 'outline',
              'onUpdate:modelValue': (next: boolean) => {
                value.value = next;
              },
            },
            () => '切换',
          ),
        ],
      }),
    );
    const badge = container.querySelector('[data-slot="badge"]');
    expect(badge?.textContent).toBe('状态标签');
    expect(badge?.classList.contains('bg-destructive')).toBe(true);
    const button = container.querySelector<HTMLButtonElement>(
      '[data-slot="toggle"]',
    );
    expect(button?.classList.contains('border-input')).toBe(true);
    button?.click();
    await nextTick();
    expect(value.value).toBe(true);
    expect(button?.dataset.state).toBe('on');
    disabled.value = true;
    await nextTick();
    button?.click();
    expect(value.value).toBe(true);
    expect(errors).toEqual([]);
  });

  it('下拉框内容、长列表和键盘选择正常', async () => {
    const value = ref('');
    const { container, errors } = mount(
      defineComponent({
        setup: () => () =>
          h(
            Select,
            {
              modelValue: value.value,
              'onUpdate:modelValue': (next: string) => {
                value.value = next;
              },
            },
            () => [
              h(SelectTrigger, {}, () =>
                h(SelectValue, { placeholder: '请选择' }),
              ),
              h(SelectContent, {}, () =>
                Array.from({ length: 30 }, (_, index) =>
                  h(
                    SelectItem,
                    { value: `item-${index}` },
                    () => `选项 ${index}`,
                  ),
                ),
              ),
            ],
          ),
      }),
    );
    const trigger = container.querySelector('[data-slot="select-trigger"]');
    trigger?.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }),
    );
    await vi.waitFor(() => {
      expect(document.querySelectorAll('[role="option"]')).toHaveLength(30);
    });
    const listbox = document.querySelector('[role="listbox"]');
    listbox?.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'End', bubbles: true }),
    );
    await nextTick();
    const last = document.querySelectorAll('[role="option"]').item(29);
    last?.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }),
    );
    await vi.waitFor(() => {
      expect(value.value).toBe('item-29');
    });
    expect(errors).toEqual([]);
  });
});
