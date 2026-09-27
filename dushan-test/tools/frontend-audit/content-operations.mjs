import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function runContentOperations(api) {
  const { page, goto, test, assert, settle, work } = api;
  const ui = controls(page, assert);
  const state = JSON.parse(
    await readFile(join(work, 'content-state.json'), 'utf8'),
  );
  const core = JSON.parse(
    await readFile(join(work, 'core-state.json'), 'utf8'),
  );
  const accounts = JSON.parse(
    await readFile(join(work, 'accounts-state.json'), 'utf8'),
  );
  const save = () =>
    writeFile(join(work, 'content-state.json'), JSON.stringify(state, null, 2));
  await test('字典数据：新增、标签样式、编辑回填', async () => {
    await goto('/system/dict');
    await ui
      .rows(state.dictType.id)
      .getByText(state.dictType.record.name, { exact: true })
      .first()
      .click();
    await settle();
    const id = await ui.create(
      '新增字典数据',
      '/admin-api/system/dict/data',
      async () => {
        await ui.fill('数据标签', 'QA测试标签');
        await ui.fill('数据键值', 'qa_value');
        await ui.fill('显示排序', 1);
        await ui.select('颜色类型', '成功');
        await ui.fill('备注', '字典数据备注');
      },
    );
    state.dictData = { id };
    await save();
    await ui.rowButton(id, '修改');
    await settle();
    assert.equal(
      await ui
        .dialog()
        .getByLabel(/数据标签$/)
        .inputValue(),
      'QA测试标签',
    );
    await ui.fill('数据标签', 'QA测试标签改');
    await ui.responseDuring('/admin-api/system/dict/data/update', 'PUT', () =>
      ui.dialog().getByRole('button', { name: '确认', exact: true }).click(),
    );
    await ui.dialog().waitFor({ state: 'hidden' });
    const { body } = await api.request(
      `/admin-api/system/dict/data/get?id=${id}`,
    );
    assert.equal(body.data.label, 'QA测试标签改');
    assert.equal(body.data.colorType, 'success');
    state.dictData.record = body.data;
    await save();
  });
  await test('配置数据：新增、编辑及回填', async () => {
    await goto('/infra/config');
    await ui
      .rows(state.configType.id)
      .getByText(state.configType.record.name, { exact: true })
      .first()
      .click();
    await settle();
    const id = await ui.create(
      '新增配置数据',
      '/admin-api/infra/config',
      async () => {
        await ui.fill('配置名称', 'QA配置值');
        await ui.fill('配置键名', 'qa.audit.value');
        await ui.fill('配置键值', 'browser');
        await ui.fill('配置描述', '独立库测试');
        await ui.select('控件类型', '文本输入');
        await ui.fill('控件属性', '{}');
      },
    );
    state.configData = { id };
    await save();
    await ui.rowButton(id, '修改');
    await settle();
    await ui.fill('配置键值', 'browser-updated');
    await ui.responseDuring('/admin-api/infra/config/update', 'PUT', () =>
      ui.dialog().getByRole('button', { name: '确认', exact: true }).click(),
    );
    await ui.dialog().waitFor({ state: 'hidden' });
    const { body } = await api.request(`/admin-api/infra/config/get?id=${id}`);
    assert.equal(body.data.value, 'browser-updated');
    state.configData.record = body.data;
    await save();
  });
  await test('邮件模板：浏览器测试发送并到达本地 SMTP', async () => {
    await goto('/system/message/mail/template');
    await ui.rowButton(state.mailTemplate.id, '测试发送');
    await settle();
    await ui.fill('收件邮箱', 'recipient@example.com');
    await ui.fill('参数 code', '864209');
    await ui.responseDuring(
      '/admin-api/system/mail/template/send-mail',
      'POST',
      () =>
        ui.dialog().getByRole('button', { name: '确认', exact: true }).click(),
    );
    await ui.dialog().waitFor({ state: 'hidden' });
    const deadline = Date.now() + 15_000;
    let delivered = false;
    while (Date.now() < deadline) {
      try {
        const inbox = JSON.parse(
          await readFile(join(work, 'mail-inbox.json'), 'utf8'),
        );
        delivered = inbox.some((item) =>
          item.payload.includes('recipient@example.com'),
        );
      } catch (error) {
        if (error.code !== 'ENOENT') throw error;
      }
      if (delivered) break;
      await page.waitForTimeout(250);
    }
    assert(delivered, 'SMTP 接收器未收到邮件');
    await goto('/system/message/mail/log');
    assert((await ui.main().innerText()).includes('recipient@example.com'));
  });
  await test('公告：新增、富文本及编辑', async () => {
    await goto('/system/announcement');
    const id = await ui.create(
      '新增公告',
      '/admin-api/system/announcement',
      async () => {
        await ui.fill('公告标题', 'QA浏览器公告');
        await ui.select('公告类别', '系统维护通知');
        await ui.fill('发布人', 'QA自动化');
        await ui
          .dialog()
          .locator('[contenteditable="true"]')
          .fill('公告内容，包含中文及 123。');
      },
    );
    state.announcement = { id };
    await save();
    await ui.rowButton(id, '修改');
    await settle();
    await ui.fill('公告标题', 'QA浏览器公告改');
    await ui.responseDuring(
      '/admin-api/system/announcement/update',
      'PUT',
      () =>
        ui.dialog().getByRole('button', { name: '确认', exact: true }).click(),
    );
    await ui.dialog().waitFor({ state: 'hidden' });
    const { body } = await api.request(
      `/admin-api/system/announcement/get?id=${id}`,
    );
    assert.equal(body.data.title, 'QA浏览器公告改');
    state.announcement.record = body.data;
    await save();
  });
  await test('用户：分配测试角色并回读', async () => {
    await goto('/system/user');
    await ui.rowButton(accounts.user.id, '更多');
    await page.getByRole('menuitem', { name: '分配角色', exact: true }).click();
    await settle();
    await ui.select('角色', core.role.name);
    await page.keyboard.press('Escape');
    await ui.responseDuring(
      '/admin-api/system/permission/assign-user-role',
      'POST',
      () =>
        ui.dialog().getByRole('button', { name: '确认', exact: true }).click(),
    );
    await ui.dialog().waitFor({ state: 'hidden' });
    const { body } = await api.request(
      `/admin-api/system/permission/list-user-roles?userId=${accounts.user.id}`,
    );
    assert(body.data.includes(core.role.id));
  });
  await test('角色：分配菜单权限', async () => {
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
  });
  await test('角色：数据权限仅本人保存回填', async () => {
    await goto('/system/role');
    await ui.rowButton(core.role.id, '更多');
    await page.getByRole('menuitem', { name: '数据权限', exact: true }).click();
    await settle();
    await ui.select('权限范围', '仅本人数据权限');
    await ui.responseDuring(
      '/admin-api/system/permission/assign-role-data-scope',
      'POST',
      () =>
        ui.dialog().getByRole('button', { name: '确认', exact: true }).click(),
    );
    await ui.dialog().waitFor({ state: 'hidden' });
    const { body } = await api.request(
      `/admin-api/system/permission/role/get?id=${core.role.id}`,
    );
    assert.equal(body.data.dataScope, 5);
  });
}
