import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function runSpecialActions(api) {
  const { page, goto, test, assert, settle, work, output } = api;
  const ui = controls(page, assert);
  const infra = JSON.parse(
    await readFile(join(work, 'infra-state.json'), 'utf8'),
  );
  const accounts = JSON.parse(
    await readFile(join(work, 'accounts-state.json'), 'utf8'),
  );
  const core = JSON.parse(
    await readFile(join(work, 'core-state.json'), 'utf8'),
  );
  await test('数据源：已保存源测试真实 MySQL 连接', async () => {
    await goto('/infra/dataSourceConfig');
    await ui.rowButton(infra.dataSource.id, '更多');
    await page.getByRole('menuitem', { name: '测试', exact: true }).click();
    await settle();
    assert((await page.locator('body').innerText()).includes('连接成功'));
  });
  await test('存储配置：测试数据库存储可读写', async () => {
    await goto('/infra/file/config');
    await writeFile(
      join(output, 'storage-actions.txt'),
      await ui.main().ariaSnapshot(),
    );
    await ui.rowButton(infra.fileConfig.id, '测试');
    await settle();
    assert((await page.locator('body').innerText()).includes('成功'));
  });
  await test('用户：重置隔离测试账号密码', async () => {
    await goto('/system/user');
    await ui.rowButton(accounts.user.id, '更多');
    await page.getByRole('menuitem', { name: '重置密码', exact: true }).click();
    await settle();
    await writeFile(
      join(output, 'reset-password.txt'),
      await ui.dialog().ariaSnapshot(),
    );
    const passwords = ui.dialog().locator('input[type="password"]');
    for (const field of await passwords.all()) await field.fill('Qatest123');
    await ui.responseDuring(
      '/admin-api/system/user/update-password',
      'PUT',
      () =>
        ui.dialog().getByRole('button', { name: '确认', exact: true }).click(),
    );
    await ui.dialog().waitFor({ state: 'hidden' });
  });
  await test('删除确认：保持显示、取消不删除', async () => {
    await goto('/system/post');
    await ui.rowButton(core.post.id, '删除');
    await page.waitForTimeout(800);
    const pop = page.locator('.el-popconfirm:visible');
    assert(await pop.isVisible());
    await pop.getByRole('button', { name: '取消', exact: true }).click();
    const { body } = await api.request(
      `/admin-api/system/dept/post/get?id=${core.post.id}`,
    );
    assert.equal(body.data.id, core.post.id);
  });
  await test('任务：详情、暂停和恢复', async () => {
    await goto('/infra/job');
    const { body } = await api.request(
      '/admin-api/infra/job/page?page=1&pageSize=20',
    );
    const job = body.data.items.find(
      (item) => item.handlerName === 'infra.job.log.clean',
    );
    await ui.rowButton(job.id, '更多');
    await page.getByRole('menuitem', { name: '详情', exact: true }).click();
    await ui.dialog().waitFor();
    await settle();
    assert((await ui.dialog().innerText()).includes(job.handlerName));
    await ui.close();
    for (let index = 0; index < 2; index++) {
      await ui.rows(job.id).locator('.el-switch').last().click();
      await ui.confirm();
      await settle();
    }
    const after = await api.request(`/admin-api/infra/job/get?id=${job.id}`);
    assert.equal(after.body.data.status, job.status);
    infra.job = { id: job.id, record: after.body.data };
    await writeFile(
      join(work, 'infra-state.json'),
      JSON.stringify(infra, null, 2),
    );
  });
  await test('任务：触发一次隔离库日志清理并查看执行日志', async () => {
    await goto('/infra/job');
    await ui.rowButton(infra.job.id, '更多');
    await page.getByRole('menuitem', { name: '执行一次', exact: true }).click();
    await page
      .locator('.el-popconfirm:visible')
      .getByRole('button', { name: '确定', exact: true })
      .click();
    await settle();
    await ui.rowButton(infra.job.id, '更多');
    await page.getByRole('menuitem', { name: '执行日志', exact: true }).click();
    await settle();
    await writeFile(
      join(output, 'job-log.txt'),
      await ui.main().ariaSnapshot(),
    );
    assert((await ui.main().innerText()).includes('日志'));
  });
  await test('代码生成：从测试数据库导入表', async () => {
    await goto('/infra/codegen');
    await ui
      .main()
      .getByRole('button', { name: '导入表', exact: true })
      .click();
    await ui.select('数据源', infra.dataSource.record.name);
    await settle();
    await ui
      .dialog()
      .getByRole('textbox', { name: /表名称$/ })
      .fill('qa_codegen_record');
    await ui
      .dialog()
      .getByRole('button', { name: '搜索', exact: true })
      .click();
    await settle();
    await ui
      .dialog()
      .locator('tr[rowid="qa_codegen_record"] .vxe-cell--checkbox')
      .first()
      .click();
    await ui.responseDuring(
      '/admin-api/infra/codegen/create-list',
      'POST',
      () =>
        ui.dialog().getByRole('button', { name: '确认', exact: true }).click(),
    );
    await ui.dialog().waitFor({ state: 'hidden' });
    const { body } = await api.request(
      '/admin-api/infra/codegen/table/page?page=1&pageSize=20',
    );
    const record = body.data.items.find(
      (item) => item.tableName === 'qa_codegen_record',
    );
    assert(record);
    infra.codegen = { id: record.id, record };
    await writeFile(
      join(work, 'infra-state.json'),
      JSON.stringify(infra, null, 2),
    );
  });
  if (infra.codegen) {
    await test('代码生成：预览内容', async () => {
      await goto('/infra/codegen');
      await ui.rowButton(infra.codegen.id, '预览');
      await settle();
      await ui.dialog().waitFor();
      await writeFile(
        join(output, 'codegen-preview.txt'),
        await ui.dialog().ariaSnapshot(),
      );
      assert((await ui.dialog().innerText()).includes('.py'));
      await ui.close();
    });
  }
}
