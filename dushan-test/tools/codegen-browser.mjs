import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { join, relative, resolve } from 'node:path';
import process from 'node:process';
import { pathToFileURL } from 'node:url';

const work = resolve(process.env.DUSHAN_CODEGEN_WORKDIR);
assert(!relative(resolve('Temp'), work).startsWith('..'));
const { port } = JSON.parse(
  await readFile(join(work, 'browser-server.json'), 'utf8'),
);
const { chromium } = await import(
  pathToFileURL(process.env.PLAYWRIGHT_ENTRY).href
);
await mkdir(join(work, 'browser'), { recursive: true });
const context = await chromium.launchPersistentContext(
  join(work, 'browser/profile'),
  {
    channel: 'chrome',
    chromiumSandbox: true,
    headless: true,
    acceptDownloads: true,
    downloadsPath: join(work, 'browser/downloads'),
    viewport: { width: 1600, height: 1000 },
  },
);
const page = context.pages()[0];
page.setDefaultTimeout(12_000);
const errors = [];
const requests = [];
page.on('pageerror', (error) => errors.push(error.message));
await page.route('**/admin-api/**', async (route) => {
  const request = route.request();
  const response = await route
    .fetch({
      url: request
        .url()
        .replace('http://localhost:5777', `http://127.0.0.1:${port}`),
      headers: { ...request.headers(), origin: 'http://testserver' },
    })
    .catch((error) => {
      // 原始异常含请求头，只记录首行原因，避免输出测试凭据。
      throw new Error(`${request.url()}: ${error.message.split('\n')[0]}`);
    });
  const headers = response.headers();
  delete headers['set-cookie'];
  if (
    request.url().includes('/infra/codegen/') &&
    !request.url().includes('/download')
  ) {
    const body = await response.json();
    requests.push({ url: request.url(), code: body.code });
  }
  await route.fulfill({ response, headers });
});

const result = { success: false, requests, errors, checks: [] };
try {
  await page.goto('http://localhost:5777/Temp/codegen-fix/index.html');
  await page.getByRole('button', { name: '导入表', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog
    .getByRole('textbox', { name: '表名称', exact: true })
    .fill('qa_record');
  await dialog.getByRole('button', { name: '搜索', exact: true }).click();
  await dialog
    .getByRole('row')
    .filter({ hasText: 'qa_record' })
    .getByRole('cell')
    .first()
    .click();
  await dialog.getByRole('button', { name: '确认', exact: true }).click();
  await dialog.waitFor({ state: 'hidden' });
  await page.getByRole('button', { name: '修改', exact: true }).click();
  await page.waitForFunction(
    () =>
      document.querySelector('input[placeholder="请输入表名称"]')?.value ===
      'qa_record',
  );
  await page
    .getByRole('textbox', { name: '备注', exact: true })
    .fill('浏览器完整流程通过');
  await page.getByRole('button', { name: '下一步', exact: true }).click();
  await page.getByRole('button', { name: '下一步', exact: true }).click();
  assert.equal(
    await page
      .getByRole('textbox', { name: '模块名', exact: false })
      .inputValue(),
    'qa',
  );
  assert.equal(
    await page
      .getByRole('textbox', { name: '业务名', exact: false })
      .inputValue(),
    'record',
  );
  await page
    .getByText('Vue3 Vben5 Element Plus', { exact: true })
    .first()
    .waitFor();
  result.checks.push('导入、详情请求和生成配置回填');

  await page
    .getByRole('combobox', { name: '生成模板', exact: true })
    .press('Enter');
  await page.getByRole('option', { name: '树形 CRUD', exact: true }).click();
  await page
    .getByRole('combobox', { name: '父编号字段', exact: false })
    .waitFor();
  await page
    .getByRole('combobox', { name: '生成模板', exact: true })
    .press('Enter');
  await page.getByRole('option', { name: '主子表 CRUD', exact: true }).click();
  await page
    .getByRole('combobox', { name: '关联主表', exact: false })
    .waitFor();
  await page
    .getByRole('combobox', { name: '生成模板', exact: true })
    .press('Enter');
  await page.getByRole('option', { name: '基础 CRUD', exact: true }).click();
  assert.equal(
    await page
      .getByRole('textbox', { name: '模块名', exact: false })
      .inputValue(),
    'qa',
  );
  result.checks.push('树表、主子表、CRUD切换不丢基础配置');

  await page
    .getByRole('combobox', { name: '上级菜单', exact: false })
    .press('Enter');
  await page.getByRole('option', { name: '顶级菜单', exact: true }).click();
  const saving = page.waitForResponse((response) =>
    response.url().includes('/infra/codegen/update'),
  );
  await page.getByRole('button', { name: '保存', exact: true }).click();
  assert.equal((await (await saving).json()).code, 0);
  await page.getByRole('button', { name: '修改', exact: true }).waitFor();
  await page.getByRole('button', { name: '修改', exact: true }).click();
  await page.waitForFunction(
    () =>
      document.querySelector('[placeholder="请输入备注"]')?.value ===
      '浏览器完整流程通过',
  );
  await page.getByRole('button', { name: '下一步', exact: true }).click();
  await page.getByRole('button', { name: '下一步', exact: true }).click();
  await page.getByText('顶级菜单', { exact: true }).first().waitFor();
  await page.screenshot({ path: join(work, 'browser/configuration.png') });
  result.checks.push('顶级菜单0保存、列表刷新、再次读取');
  await page.getByRole('button', { name: '返回', exact: true }).click();

  await page.getByRole('button', { name: '预览', exact: true }).click();
  await page
    .getByRole('dialog')
    .getByText('14 个文件', { exact: true })
    .waitFor();
  await page
    .getByRole('dialog')
    .getByRole('treeitem', { name: 'data.ts', exact: true })
    .click();
  const code = await page
    .getByRole('dialog')
    .locator('code:visible')
    .innerText();
  assert(!code.includes('hasAccessByCodes'));
  assert(code.includes("slots: { default: 'actions' }"));
  await page.screenshot({ path: join(work, 'browser/preview.png') });
  await page
    .getByRole('dialog')
    .locator('button[data-slot="dialog-close"]')
    .click();
  result.checks.push('14文件预览与新模板');

  await page.getByRole('button', { name: '更多', exact: true }).click();
  const pendingDownload = page.waitForEvent('download');
  await page.getByRole('menuitem', { name: '生成代码', exact: true }).click();
  const download = await pendingDownload;
  const destination = join(work, 'browser/codegen-record.zip');
  await download.saveAs(destination);
  assert.equal(await download.failure(), null);
  const zip = await readFile(destination);
  assert.equal(zip.subarray(0, 2).toString(), 'PK');
  result.downloadBytes = zip.length;
  result.checks.push('浏览器ZIP下载落盘');
  await page.getByRole('menu', { name: '更多' }).waitFor({ state: 'hidden' });
  await page.getByRole('button', { name: '更多', exact: true }).click();
  await page.getByRole('menuitem', { name: '同步', exact: true }).click();
  const syncing = page.waitForResponse((response) =>
    response.url().includes('/infra/codegen/sync-from-db'),
  );
  await page
    .locator('.el-popconfirm:visible')
    .getByRole('button', { name: '确定', exact: true })
    .click();
  assert.equal((await (await syncing).json()).code, 0);
  result.checks.push('同步表结构确认和接口');
  assert.deepEqual(errors, []);
  assert(requests.every((request) => request.code === 0));
  result.success = true;
} catch (error) {
  result.failure = error.stack;
  result.snapshot = await page.locator('body').ariaSnapshot();
  await page.screenshot({ path: join(work, 'browser/failure.png') });
  process.exitCode = 1;
} finally {
  await page.unrouteAll({ behavior: 'wait' });
  await context.close();
  await writeFile(
    join(work, 'browser-result.json'),
    JSON.stringify(result, null, 2),
  );
  await writeFile(
    join(work, 'browser-done.json'),
    JSON.stringify({ success: result.success }),
  );
}
console.log(
  JSON.stringify(
    {
      success: result.success,
      checks: result.checks,
      failure: result.failure,
      errors,
    },
    null,
    2,
  ),
);
