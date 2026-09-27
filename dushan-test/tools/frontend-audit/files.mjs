import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function runFiles(api) {
  const { page, goto, test, assert, settle, work, output } = api;
  const ui = controls(page, assert);
  const state = JSON.parse(
    await readFile(join(work, 'infra-state.json'), 'utf8'),
  );
  const name = 'QA文件空格 中文.txt';
  const content = 'Native 浏览器上传下载内容校验\n123456789\n';
  await writeFile(join(output, name), content);
  const row = () =>
    ui
      .main()
      .locator('.file-list__row')
      .filter({ has: page.getByRole('button', { name, exact: true }) });
  const created = await test('文件空间：切换测试存储、新建文件夹', async () => {
    await goto('/infra/file/list');
    await ui
      .main()
      .getByRole('combobox', { name: '存储空间', exact: true })
      .press('Enter');
    await page
      .getByRole('option')
      .filter({ hasText: state.fileConfig.record.name })
      .click();
    await ui
      .main()
      .getByRole('button', { name: '新建文件夹', exact: true })
      .click();
    await ui.dialog().getByPlaceholder('请输入文件夹名称').fill('QA文件夹');
    await ui
      .dialog()
      .getByRole('button', { name: '确定', exact: true })
      .click();
    await ui.dialog().waitFor({ state: 'hidden' });
    await settle();
    await ui
      .main()
      .getByRole('button', { name: 'QA文件夹', exact: true })
      .click();
    await settle();
    assert((await ui.main().innerText()).includes('QA文件夹'));
  });
  if (created.status !== 'passed') return;
  const uploaded = await test('文件空间：上传中文文件与目录内容', async () => {
    await ui
      .main()
      .locator('input[type="file"]')
      .setInputFiles(join(output, name));
    await ui
      .main()
      .getByRole('button', { name, exact: true })
      .waitFor({ timeout: 20_000 });
    await settle();
    assert((await row().innerText()).includes('text/plain'));
  });
  if (uploaded.status !== 'passed') return;
  await test('文件空间：预览文本内容', async () => {
    await ui.main().getByRole('button', { name, exact: true }).click();
    await ui.dialog().waitFor();
    await settle();
    assert(
      (await ui.dialog().innerText()).includes('Native 浏览器上传下载内容校验'),
    );
    await ui
      .dialog()
      .getByRole('button', { name: /关闭|Close/ })
      .click();
  });
  await test('文件空间：下载内容逐字一致', async () => {
    await row().getByRole('button', { name: '更多操作', exact: true }).click();
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 15_000 }),
      page.getByRole('menuitem', { name: '下载', exact: true }).click(),
    ]);
    await download.saveAs(join(output, 'downloaded.txt'));
    assert.equal(
      await readFile(join(output, 'downloaded.txt'), 'utf8'),
      content,
    );
  });
  await test('文件空间：搜索与列表网格切换', async () => {
    await ui
      .main()
      .getByPlaceholder('搜索此文件夹及其子目录')
      .fill('不存在文件');
    await ui.main().getByPlaceholder('搜索此文件夹及其子目录').press('Enter');
    await settle();
    assert.equal(await ui.main().locator('.file-list__row').count(), 0);
    await ui.main().getByPlaceholder('搜索此文件夹及其子目录').fill('中文');
    await ui.main().getByPlaceholder('搜索此文件夹及其子目录').press('Enter');
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
  await test('文件空间：重命名', async () => {
    await row().getByRole('button', { name: '更多操作', exact: true }).click();
    await page.getByRole('menuitem', { name: '重命名', exact: true }).click();
    await ui.dialog().getByRole('textbox').fill('QA重命名文件.txt');
    await ui
      .dialog()
      .getByRole('button', { name: '确定', exact: true })
      .click();
    await ui.dialog().waitFor({ state: 'hidden' });
    await ui.main().getByPlaceholder('搜索此文件夹及其子目录').fill('');
    await ui.main().getByPlaceholder('搜索此文件夹及其子目录').press('Enter');
    await settle();
    await ui
      .main()
      .getByRole('button', { name: 'QA重命名文件.txt', exact: true })
      .waitFor();
  });
  await test('文件空间：选中与批量删除测试文件', async () => {
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
