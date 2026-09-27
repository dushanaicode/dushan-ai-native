import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function runExports(api) {
  const { page, goto, test, assert, work, output, settle } = api;
  const ui = controls(page, assert);
  const entries = JSON.parse(
    await readFile(join(work, 'page-inventory.json'), 'utf8'),
  );
  const downloads = [];
  for (const entry of entries) {
    await goto(entry.path);
    const count = await ui
      .main()
      .getByRole('button', { name: '导出', exact: true })
      .count();
    for (let index = 0; index < count; index++) {
      await test(`${entry.name}：导出 ${index + 1} 并核验下载文件`, async () => {
        await goto(entry.path);
        await ui
          .main()
          .getByRole('button', { name: '导出', exact: true })
          .nth(index)
          .click();
        await ui.dialog().waitFor();
        await settle();
        const [download] = await Promise.all([
          page.waitForEvent('download', { timeout: 20_000 }),
          ui
            .dialog()
            .getByRole('button', { name: /导出/, exact: false })
            .click(),
        ]);
        const file = `${String(downloads.length + 1).padStart(2, '0')}-${download.suggestedFilename()}`;
        await download.saveAs(join(output, file));
        const buffer = await readFile(join(output, file));
        const magic = buffer.subarray(0, 4).toString('hex');
        assert(
          ['504b0304', 'd0cf11e0'].includes(magic),
          `下载不是 Excel：${magic}`,
        );
        assert(buffer.length > 1000);
        downloads.push({ page: entry.path, file, bytes: buffer.length, magic });
        await writeFile(
          join(output, 'downloads.json'),
          JSON.stringify(downloads, null, 2),
        );
        return downloads.at(-1);
      });
    }
  }
  await test('用户导入：下载 Excel 模板', async () => {
    await goto('/system/user');
    await ui.main().getByRole('button', { name: '导入', exact: true }).click();
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      ui
        .dialog()
        .getByRole('button', { name: '下载模板', exact: true })
        .click(),
    ]);
    await download.saveAs(join(work, 'user-import-template.xlsx'));
    const buffer = await readFile(join(work, 'user-import-template.xlsx'));
    assert.equal(buffer.subarray(0, 4).toString('hex'), '504b0304');
    await ui.close();
  });
}
