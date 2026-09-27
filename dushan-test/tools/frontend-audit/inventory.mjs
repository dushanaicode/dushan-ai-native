import { writeFile } from 'node:fs/promises';
import { join } from 'node:path';

export default async function runInventory({ page, login, test, output }) {
  await test('真实登录与初始菜单', async () => {
    await login();
    await writeFile(
      join(output, 'initial-ui.txt'),
      await page.locator('body').ariaSnapshot(),
    );
    await page.screenshot({ path: join(output, 'dashboard.png') });
    return { url: page.url() };
  });
}
