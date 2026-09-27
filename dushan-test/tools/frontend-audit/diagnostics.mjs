import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function runDiagnostics(api) {
  const { page, goto, test, assert, settle, work, output } = api;
  const ui = controls(page, assert);
  const core = JSON.parse(
    await readFile(join(work, 'core-state.json'), 'utf8'),
  );
  const accounts = JSON.parse(
    await readFile(join(work, 'accounts-state.json'), 'utf8'),
  );
  await goto('/system/role');
  await test('用户角色回填：检查雪花 ID 精度', async () => {
    const roles = await api.request(
      `/admin-api/system/permission/list-user-roles?userId=${accounts.user.id}`,
    );
    await writeFile(
      join(output, 'role-id-response.json'),
      JSON.stringify({ expected: core.role.id, response: roles.body }, null, 2),
    );
    await goto('/system/user');
    await ui.rowButton(accounts.user.id, '更多');
    await page.getByRole('menuitem', { name: '分配角色', exact: true }).click();
    await settle();
    await writeFile(
      join(output, 'role-refill.txt'),
      await ui.dialog().ariaSnapshot(),
    );
    assert.equal(
      String(roles.body.data[0]),
      core.role.id,
      'JSON 数字导致角色 ID 在浏览器中失真',
    );
    assert(
      (await ui.dialog().innerText()).includes(core.role.name),
      '角色名称未正确回填',
    );
  });
  await test('租户初始化数据：菜单为空证据及测试数据补全', async () => {
    await goto('/system/tenant-manage/tenantPackage');
    const list = await api.request('/admin-api/system/permission/menu/list');
    const simple = await api.request(
      '/admin-api/system/permission/menu/simple-list',
    );
    const tenants = await api.request(
      '/admin-api/system/tenant/page?page=1&pageSize=20',
    );
    const tenant = tenants.body.data.items[0];
    const existing = await api.request(
      `/admin-api/system/tenant/package/get?id=${tenant.packageId}`,
    );
    const { id, name, status, menuIds, quotaConfig, remark } =
      existing.body.data;
    await writeFile(
      join(output, 'seed-package.json'),
      JSON.stringify(
        {
          tenantId: tenant.id,
          packageId: id,
          packageMenuIds: menuIds,
          totalMenus: list.body.data.length,
          simpleMenus: simple.body.data.length,
        },
        null,
        2,
      ),
    );
    const response = await api.request(
      '/admin-api/system/tenant/package/update',
      {
        method: 'PUT',
        data: {
          id,
          name,
          status,
          quotaConfig,
          remark,
          menuIds: list.body.data.map((item) => item.id),
        },
      },
    );
    assert.equal(response.body.code, 0);
    const after = await api.request(
      '/admin-api/system/permission/menu/simple-list',
    );
    assert(after.body.data.length > 0);
    return {
      scope: '仅隔离测试库补齐套餐菜单以继续授权测试，未修改产品 SQL',
      before: menuIds.length,
      after: after.body.data.length,
    };
  });
  await test('租户套餐：菜单树选择、新增与编辑', async () => {
    await goto('/system/tenant-manage/tenantPackage');
    const id = await ui.create(
      '新增租户套餐',
      '/admin-api/system/tenant/package',
      async () => {
        await ui.fill('套餐名称', 'QA浏览器套餐');
        await settle();
        await writeFile(
          join(output, 'tenant-package-tree.txt'),
          await ui.dialog().ariaSnapshot(),
        );
        await ui.dialog().getByRole('checkbox').first().click();
        await ui.fill('备注', '隔离库套餐');
      },
    );
    const { body } = await api.request(
      `/admin-api/system/tenant/package/get?id=${id}`,
    );
    assert(body.data.menuIds.length > 0);
    accounts.tenantPackage = { id, record: body.data };
    await writeFile(
      join(work, 'accounts-state.json'),
      JSON.stringify(accounts, null, 2),
    );
    await ui.rowButton(id, '修改');
    await settle();
    await ui.fill('套餐名称', 'QA浏览器套餐改');
    await ui.responseDuring(
      '/admin-api/system/tenant/package/update',
      'PUT',
      () =>
        ui.dialog().getByRole('button', { name: '确认', exact: true }).click(),
    );
    await ui.dialog().waitFor({ state: 'hidden' });
    accounts.tenantPackage.record = (
      await api.request(`/admin-api/system/tenant/package/get?id=${id}`)
    ).body.data;
    await writeFile(
      join(work, 'accounts-state.json'),
      JSON.stringify(accounts, null, 2),
    );
  });
  await test('角色菜单授权：补齐隔离库套餐后保存并回读', async () => {
    await goto('/system/role');
    await ui.rowButton(core.role.id, '更多');
    await page.getByRole('menuitem', { name: '菜单权限', exact: true }).click();
    await settle();
    await ui.dialog().getByText('全选', { exact: true }).click();
    await ui.responseDuring(
      '/admin-api/system/permission/assign-role-menu',
      'POST',
      () =>
        ui.dialog().getByRole('button', { name: '确认', exact: true }).click(),
    );
    await ui.dialog().waitFor({ state: 'hidden' });
    const { body } = await api.request(
      `/admin-api/system/permission/list-role-menus?roleId=${core.role.id}`,
    );
    assert(body.data.length > 0);
    return { menuCount: body.data.length };
  });
  await test('邮件异步状态：查询发送日志与消费日志', async () => {
    await goto('/system/message/mail/log');
    const mail = await api.request(
      '/admin-api/system/mail/log/page?page=1&pageSize=20',
    );
    const mq = await api.request(
      '/admin-api/infra/mq/log/page?page=1&pageSize=20',
    );
    await writeFile(
      join(output, 'mail-delivery-state.json'),
      JSON.stringify({ mail: mail.body, mq: mq.body }, null, 2),
    );
    assert.equal(
      mail.body.data.items[0].sendStatus,
      10,
      '接口提示成功后，邮件仍未发送成功',
    );
  });
}
