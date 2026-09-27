import { Buffer } from 'node:buffer';
import { existsSync } from 'node:fs';
import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function runAdminCrud(api) {
  const { page, goto, test, assert, settle, work, server, output } = api;
  const ui = controls(page, assert);
  const state = existsSync(join(work, 'admin-state.json'))
    ? JSON.parse(await readFile(join(work, 'admin-state.json'), 'utf8'))
    : {};
  const save = () =>
    writeFile(join(work, 'admin-state.json'), JSON.stringify(state, null, 2));
  const logo = join(output, 'qa-logo.png');
  await writeFile(
    logo,
    Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aC1cAAAAASUVORK5CYII=',
      'base64',
    ),
  );
  const cases = [
    {
      key: 'menu',
      title: '菜单',
      path: '/system/menu',
      endpoint: '/admin-api/system/permission/menu',
      label: '菜单名称',
      property: 'name',
      value: 'QA操作按钮',
      async fill() {
        await ui.fill('菜单名称', 'QA操作按钮');
        await ui.dialog().getByText('按钮', { exact: true }).click();
        await ui.select('上级菜单', '用户管理');
        await ui.fill('权限标识', 'qa:browser:action');
      },
    },
    {
      key: 'tenant',
      title: '租户',
      path: '/system/tenant-manage/tenant',
      endpoint: '/admin-api/system/tenant',
      label: '租户名称',
      property: 'name',
      value: 'QA浏览器租户',
      async fill() {
        await ui.fill('租户名称', 'QA浏览器租户');
        await ui.select('租户套餐', '标准套餐');
        await ui.fill('联系人', 'QA负责人');
        await ui.fill('联系手机', '13900139002');
        await ui.fill('用户账号', 'qatenant');
        await ui.fill('用户密码', 'Qatest123');
        await ui.fill('账号额度', 10);
        await ui
          .dialog()
          .getByRole('combobox', { name: /过期时间$/ })
          .fill('2030-12-31 23:59:59');
        await ui
          .dialog()
          .getByRole('combobox', { name: /过期时间$/ })
          .press('Enter');
        await page.keyboard.press('Tab');
        await ui.fill('绑定域名', 'https://qa.example.com');
      },
    },
    {
      key: 'oauthClient',
      title: 'OAuth2 客户端',
      path: '/system/oauth2/client',
      endpoint: '/admin-api/system/oauth2/client',
      label: '客户端名称',
      property: 'name',
      value: 'QA客户端',
      async fill() {
        await ui.fill('客户端编号', 'qa_browser');
        await ui.fill('客户端密钥', 'QA-client-secret-123456-abcdefg-HIJK!');
        await ui.fill('客户端名称', 'QA客户端');
        await ui.dialog().locator('input[type="file"]').setInputFiles(logo);
        await settle();
        const redirect = ui
          .dialog()
          .getByRole('combobox', { name: /重定向地址$/ });
        await redirect.fill(`${server.origin}/callback`);
        await page
          .getByRole('option', {
            name: `${server.origin}/callback`,
            exact: true,
          })
          .click();
        await page.keyboard.press('Escape');
        await ui
          .dialog()
          .getByRole('combobox', { name: /授权类型$/ })
          .press('Enter');
        await writeFile(
          join(output, 'oauth-grants.txt'),
          await page.locator('body').ariaSnapshot(),
        );
        await page
          .getByRole('option')
          .filter({ hasText: /密码/ })
          .click();
        await page.keyboard.press('Escape');
        await ui.fill('客户端描述', '隔离测试客户端');
      },
    },
    {
      key: 'socialClient',
      title: '社交客户端',
      path: '/system/social/client',
      endpoint: '/admin-api/system/social/client',
      label: '应用名',
      property: 'name',
      value: 'QA社交应用',
      async fill() {
        await ui.fill('应用名', 'QA社交应用');
        await ui
          .dialog()
          .getByRole('combobox', { name: /社交平台$/ })
          .press('Enter');
        await writeFile(
          join(output, 'social-providers.txt'),
          await page.locator('body').ariaSnapshot(),
        );
        await page
          .getByRole('option', { name: 'DINGTALK', exact: true })
          .click();
        await ui.fill('客户端编号', 'qa-social-client');
        await ui.fill('密钥 / 私钥', 'qa-social-secret');
      },
    },
  ];
  for (const config of cases) {
    let id;
    await test(`${config.title}：新增与持久化`, async () => {
      await goto(config.path);
      id = await ui.create(`新增${config.title}`, config.endpoint, config.fill);
      await settle();
      const { body } = await api.request(`${config.endpoint}/get?id=${id}`);
      assert.equal(body.code, 0);
      assert.equal(body.data[config.property], config.value);
      state[config.key] = { id, record: body.data };
      await save();
    });
    if (!id) continue;
    await test(`${config.title}：编辑与回填`, async () => {
      await ui.rowButton(id, '修改');
      await settle();
      await ui.fill(config.label, `${config.value}改`);
      await ui.responseDuring(`${config.endpoint}/update`, 'PUT', () =>
        ui.dialog().getByRole('button', { name: '确认', exact: true }).click(),
      );
      await ui.dialog().waitFor({ state: 'hidden' });
      const { body } = await api.request(`${config.endpoint}/get?id=${id}`);
      assert.equal(body.data[config.property], `${config.value}改`);
      state[config.key].record = body.data;
      await save();
    });
  }
}
