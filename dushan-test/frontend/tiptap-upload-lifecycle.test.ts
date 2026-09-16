import { expect, it, vi } from 'vitest';

import { Editor } from '../../dushan-admin-frontend/packages/effects/plugins/node_modules/@tiptap/core/dist/index.js';
import { createDefaultTiptapExtensions } from '../../dushan-admin-frontend/packages/effects/plugins/src/tiptap/extensions';

it('真实编辑器文件选择取消和销毁会释放隐藏input', () => {
  const element = document.createElement('div');
  document.body.append(element);
  const editor = new Editor({
    element,
    extensions: createDefaultTiptapExtensions({
      imageUpload: { upload: vi.fn(async () => '/files/image') },
    }),
  });
  const inputs: HTMLInputElement[] = [];
  try {
    editor.commands.uploadImage();
    const first =
      document.querySelector<HTMLInputElement>('input[type="file"]')!;
    inputs.push(first);
    expect(first.isConnected).toBe(true);
    first.dispatchEvent(new Event('cancel'));
    expect(first.isConnected).toBe(false);
    editor.commands.uploadImage();
    const second =
      document.querySelector<HTMLInputElement>('input[type="file"]')!;
    inputs.push(second);
    editor.destroy();
    expect(second.isConnected).toBe(false);
  } finally {
    editor.destroy();
    for (const input of inputs) input.remove();
    element.remove();
  }
});
