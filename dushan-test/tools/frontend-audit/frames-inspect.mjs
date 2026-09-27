import { writeFile } from 'node:fs/promises';
import { join } from 'node:path';
export default async function runFramesInspect(api) {
  const { page, goto, output } = api;
  for (const [name, path] of [
    ['docs', '/infra/docs'],
    ['monitor', '/infra/monitor-dashboard'],
  ]) {
    await goto(path);
    await page.waitForTimeout(1500);
    const data = [];
    for (const frame of page
      .frames()
      .filter((frame) => frame !== page.mainFrame())) {
      data.push({
        url: frame.url(),
        text: (await frame.locator('body').innerText()).slice(0, 12_000),
      });
      await writeFile(
        join(output, `${name}-frame.txt`),
        await frame.locator('body').ariaSnapshot(),
      );
    }
    await writeFile(
      join(output, `${name}.json`),
      JSON.stringify(data, null, 2),
    );
    await page.screenshot({ path: join(output, `${name}.png`) });
  }
}
