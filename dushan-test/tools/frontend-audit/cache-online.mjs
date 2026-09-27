import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function runCacheOnline(api) {
  const { page, goto, test, assert, work, output, settle } = api;
  const ui = controls(page, assert);
  for (const kind of ['string', 'hash', 'list', 'set', 'zset', 'stream']) {
    await test(`Redis：${kind} 详情和删除测试 key`, async () => {
      await goto('/infra/monitor/redis-cache');
      const name = `qa_browser_${kind}`;
      await ui.main().getByPlaceholder('搜索 key，支持 * 通配符').fill(name);
      await ui
        .main()
        .getByPlaceholder('搜索 key，支持 * 通配符')
        .press('Enter');
      await settle();
      const detail = await ui.responseDuring(
        '/admin-api/infra/cache/monitor/key-detail',
        'GET',
        () => ui.main().getByText(name, { exact: true }).first().click(),
      );
      assert.equal(detail.keyType, kind);
      assert(JSON.stringify(detail.value).includes('QA_'));
      const panel = ui.main().locator('.el-card').filter({ hasText: 'Value' });
      await panel.getByRole('button', { name: '删除', exact: true }).click();
      await ui.responseDuring(
        '/admin-api/infra/cache/monitor/delete-key',
        'DELETE',
        () =>
          page
            .locator('.el-message-box:visible')
            .getByRole('button', { name: '删除', exact: true })
            .click(),
      );
      await settle();
    });
  }
  const accounts = JSON.parse(
    await readFile(join(work, 'accounts-state.json'), 'utf8'),
  );
  const allowedCodes = [];
  await test(
    '在线用户：强退隔离测试会话并验证失效',
    async () => {
      await goto('/infra/monitor/online');
      const before = (
        await api.request('/admin-api/infra/online/list?page=1&pageSize=200')
      ).body.data.items;
      const login = await api.request('/admin-api/system/auth/login', {
        method: 'POST',
        auth: false,
        credentials: 'omit',
        headers: { 'X-Tenant-Id': '1' },
        data: {
          username: accounts.user.record.username,
          password: 'Qatest123',
        },
      });
      assert.equal(login.body.code, 0);
      const after = (
        await api.request('/admin-api/infra/online/list?page=1&pageSize=200')
      ).body.data.items;
      const target = after.find(
        (row) => !before.some((old) => old.tokenId === row.tokenId),
      );
      assert(target);
      assert(target.ipaddr && target.os && target.browser);
      await page.reload();
      await settle();
      await ui.rowButton(target.tokenId, '强退');
      await ui.responseDuring(
        '/admin-api/infra/online/force-logout',
        'DELETE',
        () =>
          page
            .locator('.el-popconfirm:visible')
            .getByRole('button', { name: '确定', exact: true })
            .click(),
      );
      const rejected = await api.request(
        '/admin-api/system/auth/get-permission-info',
        {
          auth: false,
          headers: { Authorization: `Bearer ${login.body.data.accessToken}` },
        },
      );
      allowedCodes.push(rejected.body.code);
      assert.notEqual(rejected.body.code, 0);
      return { code: rejected.body.code, metadataPresent: true };
    },
    { allowedCodes },
  );
  await test('子页面路由：代码生成编辑、任务日志、MQ 日志注册情况', async () => {
    await goto('/infra/codegen');
    const routes = await page.evaluate(() => {
      const router =
        document.querySelector('#app').__vue_app__.config.globalProperties
          .$router;
      return ['InfraCodegenEdit', 'InfraJobLog', 'InfraMqLog'].map((name) => ({
        name,
        registered: router.hasRoute(name),
      }));
    });
    await writeFile(
      join(output, 'nested-routes.json'),
      JSON.stringify(routes, null, 2),
    );
    assert(
      routes.every((route) => route.registered),
      JSON.stringify(routes),
    );
  });
}
