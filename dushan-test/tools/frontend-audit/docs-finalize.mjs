import { writeFile } from 'node:fs/promises';
import { join } from 'node:path';
export default async function runDocsFinalize(api) {
  const { page, goto, test, assert, output } = api;
  await test('API 文档：Swagger 滚动定位业务接口和 ReDoc 展示', async () => {
    await goto('/infra/docs');
    const frame = page.frameLocator('iframe');
    await frame.locator('.swagger-ui').waitFor({ timeout: 20_000 });
    const bounds = await page.locator('iframe').boundingBox();
    await page.mouse.move(
      bounds.x + bounds.width / 2,
      bounds.y + bounds.height / 2,
    );
    const link = frame
      .locator('a[href*="get_user_page_admin_api_system_user_page_get"]')
      .first();
    for (let index = 0; index < 60 && (await link.count()) === 0; index++) {
      await page.mouse.wheel(0, 600);
      await page.waitForTimeout(120);
    }
    await link.scrollIntoViewIfNeeded({ timeout: 25_000 });
    await link.waitFor();
    assert((await link.innerText()).includes('/admin-api/system/user/page'));
    await writeFile(join(output, 'swagger.txt'), await link.innerText());
    await page
      .locator('#__vben_main_content')
      .getByText('ReDoc', { exact: true })
      .click();
    await frame.locator('.redoc-wrap').waitFor({ timeout: 25_000 });
    await writeFile(join(output, 'redoc.txt'), 'ReDoc 内页组件已加载');
    await page.screenshot({ path: join(output, 'redoc.png') });
  });
}
