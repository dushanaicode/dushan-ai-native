import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import process from 'node:process';

import { controls } from './ui.mjs';

export default async function runFilesResume(api) {
  const { page, goto, test, assert, settle, work, output } = api;
  const ui = controls(page, assert);
  if (process.env.DUSHAN_AUDIT_BROWSER) await api.login();
  const state = JSON.parse(
    await readFile(join(work, 'infra-state.json'), 'utf8'),
  );
  const name = 'QA重命名文件.txt';
  const folder = async () => {
    await goto('/infra/file/list');
    await page.reload();
    await settle();
    await ui
      .main()
      .getByRole('combobox', { name: '存储空间', exact: true })
      .press('Enter');
    await page
      .getByRole('option')
      .filter({ hasText: state.fileConfig.record.name })
      .click();
    await settle();
    await ui
      .main()
      .getByRole('button', { name: 'QA文件夹', exact: true })
      .click();
    await settle();
  };
  const row = () =>
    ui
      .main()
      .locator('.file-list__row')
      .filter({ has: page.getByRole('button', { name, exact: true }) });
  await test('文件空间：下载已有文件并核验内容', async () => {
    await folder();
    await row().getByRole('button', { name: '更多操作', exact: true }).click();
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 15_000 }),
      page.getByRole('menuitem', { name: '下载', exact: true }).click(),
    ]);
    await download.saveAs(join(output, 'downloaded.txt'));
    assert.equal(
      await readFile(join(output, 'downloaded.txt'), 'utf8'),
      'Native 浏览器上传下载内容校验\n123456789\n',
    );
  });
  await test('文件空间：搜索与两种视图切换', async () => {
    await folder();
    const search = ui.main().getByPlaceholder('搜索此文件夹及其子目录');
    await search.fill('不存在文件');
    await search.press('Enter');
    await settle();
    assert.equal(await ui.main().locator('.file-list__row').count(), 0);
    await search.fill('QA重命名');
    await search.press('Enter');
    await settle();
    await ui.main().getByRole('button', { name, exact: true }).waitFor();
    await ui
      .main()
      .getByRole('button', { name: '网格视图', exact: true })
      .click();
    await page.screenshot({ path: join(output, 'grid.png') });
    await ui
      .main()
      .getByRole('button', { name: '列表视图', exact: true })
      .click();
  });
  await test('文件空间：重命名文件', async () => {
    await folder();
    await row().getByRole('button', { name: '更多操作', exact: true }).click();
    await page.getByRole('menuitem', { name: '重命名', exact: true }).click();
    await ui.dialog().getByRole('textbox').fill('QA重命名文件.txt');
    await ui
      .dialog()
      .getByRole('button', { name: '确定', exact: true })
      .click();
    await ui.dialog().waitFor({ state: 'hidden' });
    await settle();
    await ui
      .main()
      .getByRole('button', { name: 'QA重命名文件.txt', exact: true })
      .waitFor();
  });
  await test('文件空间：勾选与批量删除测试文件', async () => {
    await folder();
    await ui
      .main()
      .getByRole('checkbox', { name: /QA重命名文件/ })
      .check();
    await ui
      .main()
      .getByRole('button', { name: /删除选中/ })
      .click();
    await ui.confirm();
    await settle();
    assert.equal(
      await ui
        .main()
        .getByRole('button', { name: 'QA重命名文件.txt', exact: true })
        .count(),
      0,
    );
  });
}
