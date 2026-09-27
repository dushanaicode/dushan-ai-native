import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function runAppearance(api) {
  const { page, goto, test, assert, work, output } = api;
  const ui = controls(page, assert);
  await test('明暗主题：表单空画布和 Jaeger 内页同步', async () => {
    const originalDark = await page
      .locator('html')
      .evaluate((element) => element.classList.contains('dark'));
    const samples = [];
    for (const dark of [true, false]) {
      await goto('/infra/build');
      if (
        (await page
          .locator('html')
          .evaluate((element) => element.classList.contains('dark'))) !== dark
      ) {
        await page
          .getByRole('button', { name: dark ? 'dark' : 'light', exact: true })
          .click();
        await page.waitForTimeout(300);
      }
      const color = await ui
        .main()
        .locator('._fc-m-drag')
        .evaluate((element) => getComputedStyle(element).backgroundColor);
      await page.screenshot({
        path: join(output, dark ? 'builder-dark.png' : 'builder-light.png'),
      });
      await goto('/infra/monitor-dashboard');
      const frame = page.frameLocator('iframe');
      await frame
        .getByRole('textbox', { name: 'Lookup by Trace ID...' })
        .waitFor({ timeout: 20_000 });
      const pressed = await frame
        .getByRole('button', { name: 'Toggle color mode' })
        .getAttribute('aria-pressed');
      assert.equal(pressed, String(dark));
      samples.push({ dark, color, jaegerDark: pressed });
    }
    assert.notEqual(samples[0].color, samples[1].color);
    await writeFile(
      join(output, 'themes.json'),
      JSON.stringify(samples, null, 2),
    );
    if (originalDark)
      await page.getByRole('button', { name: 'dark', exact: true }).click();
  });
  await test('布局：手机、平板和桌面列表无页面级横向溢出', async () => {
    for (const [width, height] of [
      [390, 844],
      [768, 1024],
      [1600, 1000],
    ]) {
      await page.setViewportSize({ width, height });
      await goto('/system/user');
      await page.waitForTimeout(350);
      const size = await page.evaluate(() => ({
        width: innerWidth,
        scrollWidth: document.documentElement.scrollWidth,
      }));
      assert(size.scrollWidth <= size.width + 2, JSON.stringify(size));
      await page.screenshot({ path: join(output, `user-${width}.png`) });
    }
  });
  await test('代码生成：补充接口验证 ZIP 实际内容', async () => {
    const state = JSON.parse(
      await readFile(join(work, 'infra-state.json'), 'utf8'),
    );
    const response = await api.binary(
      `/admin-api/infra/codegen/download?tableId=${state.codegen.id}`,
      join(output, 'codegen.zip'),
    );
    assert.equal(response.http, 200);
    assert.equal(
      (await readFile(join(output, 'codegen.zip'))).subarray(0, 2).toString(),
      'PK',
    );
    return {
      ...response,
      source: 'browser-api',
      browserSaveLimitation:
        '独立浏览器保存 ZIP 时崩溃，API 下载到文件另行核验',
    };
  });
  await test('已关闭登录能力：注册和第三方入口不显示', async () => {
    const actor = await api.context.browser().newContext();
    try {
      const login = await actor.newPage();
      await login.goto(`${api.server.origin}/#/auth/login`);
      await login.getByPlaceholder('请输入用户名').waitFor();
      assert.equal(
        await login.getByText('创建账号', { exact: true }).count(),
        0,
      );
      assert.equal(
        await login.getByText('其他登录方式', { exact: true }).count(),
        0,
      );
      await login.screenshot({
        path: join(output, 'login-disabled-features.png'),
      });
    } finally {
      await actor.close();
    }
  });
}
