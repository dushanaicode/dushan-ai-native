import { writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import docs from './docs-finalize.mjs';
import { controls } from './ui.mjs';

export default async function runPrimaryFinish(api) {
  const { page, test, assert, goto, settle, output } = api;
  const ui = controls(page, assert);
  await api.login();
  await docs(api);
  await test('缓存管理：隔离 Redis 清空全部的确认与执行', async () => {
    await goto('/infra/monitor/redis-cache');
    await ui
      .main()
      .getByRole('button', { name: '清空全部', exact: true })
      .click();
    const prompt = page.locator('.el-message-box:visible');
    assert((await prompt.innerText()).includes('FLUSHDB'));
    await prompt.getByRole('textbox').fill('CLEAR');
    await ui.responseDuring(
      '/admin-api/infra/cache/monitor/clear-cache-all',
      'DELETE',
      () => prompt.getByRole('button', { name: '清空', exact: true }).click(),
    );
    await settle();
    await writeFile(
      join(output, 'clear-all.txt'),
      await ui.main().ariaSnapshot(),
    );
  });
}
