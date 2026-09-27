import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

export default async function runPages({
  page,
  goto,
  test,
  assert,
  work,
  output,
}) {
  const menus = JSON.parse(await readFile(join(work, 'menus.json'), 'utf8'));
  const entries = [
    { name: '分析页', path: '/dashboard/analytics' },
    { name: '工作台', path: '/dashboard/workspace' },
    { name: '个人中心', path: '/profile' },
  ];
  function visit(nodes, prefix) {
    for (const node of nodes) {
      const path = node.path.startsWith('/')
        ? node.path
        : `${prefix}/${node.path}`;
      if (node.kind === 'page')
        entries.push({ name: node.name, path, component: node.component });
      if (node.children) visit(node.children, path);
    }
  }
  visit(menus, '');
  await writeFile(
    join(work, 'page-inventory.json'),
    JSON.stringify(entries, null, 2),
  );
  for (const [index, entry] of entries.entries()) {
    await test(`${entry.name}：页面、初始请求与可见操作`, async () => {
      await goto(entry.path);
      const main = page.locator('#__vben_main_content');
      await main.waitFor();
      const snapshot = await main.ariaSnapshot();
      const buttons = await main
        .locator('button:visible')
        .evaluateAll((nodes) =>
          nodes.map((node) => ({
            text: node.innerText,
            title: node.title,
            label: node.getAttribute('aria-label'),
            disabled: node.disabled,
          })),
        );
      const file = String(index + 1).padStart(2, '0');
      await writeFile(join(output, `${file}.txt`), snapshot);
      await page.screenshot({ path: join(output, `${file}.png`) });
      assert(!snapshot.includes('即将推出'), '页面仍为占位页');
      assert(!snapshot.includes('页面不存在'), '路由没有对应页面');
      assert(snapshot.length > 30, '页面内容为空');
      return { ...entry, buttons };
    });
  }
}
