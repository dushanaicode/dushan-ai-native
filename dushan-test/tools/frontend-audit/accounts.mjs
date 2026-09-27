import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function runAccounts(api) {
  const { page, goto, test, assert, settle, work, server } = api;
  const ui = controls(page, assert);
  const core = JSON.parse(
    await readFile(join(work, 'core-state.json'), 'utf8'),
  );
  const state = {};
  const key = Date.now().toString(36).slice(-6);
  const cases = [
    {
      key: 'user',
      title: '用户',
      button: '新增用户',
      path: '/system/user',
      endpoint: '/admin-api/system/user',
      property: 'nickname',
      label: '用户昵称',
      value: `QA用户${key}`,
      async fill() {
        await ui.fill('用户账号', `qauser${key}`);
        await ui.fill('用户密码', 'Qatest123');
        await ui.fill('用户昵称', `QA用户${key}`);
        await ui.select('归属部门', core.dept.name);
        await ui.select('岗位', core.post.name);
        await page.keyboard.press('Escape');
        await ui.fill('邮箱', `qa${key}@example.com`);
        await ui.fill('手机号', '13900139001');
        await ui.dialog().getByText('男', { exact: true }).click();
        await ui.fill('备注', '全流程测试用户');
      },
    },
    {
      key: 'mailAccount',
      title: '邮箱账号',
      button: '新增邮箱账号',
      path: '/system/message/mail/account',
      endpoint: '/admin-api/system/mail/account',
      property: 'username',
      label: '用户名',
      value: `qa_mail_${key}`,
      async fill() {
        await ui.fill('邮箱', `qa${key}@example.com`);
        await ui.fill('用户名', `qa_mail_${key}`);
        await ui.fill('密码', 'Qatest123');
        await ui.fill('SMTP 服务器', '127.0.0.1');
        await ui.fill('SMTP 端口', server.smtpPort);
        await ui.toggle('开启 SSL', false);
        await ui.toggle('开启 STARTTLS', false);
      },
    },
    {
      key: 'smsChannel',
      title: '短信渠道',
      button: '新增短信渠道',
      path: '/system/message/sms/channel',
      endpoint: '/admin-api/system/sms/channel',
      property: 'signature',
      label: '短信签名',
      value: `QA短信${key}`,
      async fill() {
        await ui.fill('短信签名', `QA短信${key}`);
        await ui.select('渠道编码', '阿里云');
        await ui.fill('API 账号', 'qa-key');
        await ui.fill('API 密钥', 'qa-secret');
        await ui.fill('回调 URL', `${server.origin}/qa-sms-callback`);
        await ui.fill('备注', '仅本地测试适配器');
      },
    },
    {
      key: 'tenantPackage',
      title: '租户套餐',
      button: '新增租户套餐',
      path: '/system/tenant-manage/tenantPackage',
      endpoint: '/admin-api/system/tenant/package',
      property: 'name',
      label: '套餐名称',
      value: `QA套餐${key}`,
      async fill() {
        await ui.fill('套餐名称', `QA套餐${key}`);
        await ui.fill('备注', '浏览器测试套餐');
      },
    },
  ];
  for (const config of cases) {
    let id;
    await test(`${config.title}：新增与数据核验`, async () => {
      await goto(config.path);
      id = await ui.create(config.button, config.endpoint, config.fill);
      await settle();
      const response = await api.request(`${config.endpoint}/get?id=${id}`);
      assert.equal(response.body.code, 0);
      assert.equal(response.body.data[config.property], config.value);
      state[config.key] = {
        id,
        value: config.value,
        record: response.body.data,
      };
      await writeFile(
        join(work, 'accounts-state.json'),
        JSON.stringify(state, null, 2),
      );
      return { id };
    });
    if (!id) continue;
    await test(`${config.title}：编辑与回填`, async () => {
      await goto(config.path);
      await ui.rowButton(id, '修改');
      await page.waitForTimeout(250);
      assert.equal(
        await ui
          .dialog()
          .getByLabel(new RegExp(`${config.label}$`))
          .inputValue(),
        config.value,
      );
      await ui.fill(config.label, `${config.value}改`);
      await ui.responseDuring(`${config.endpoint}/update`, 'PUT', () =>
        ui.dialog().getByRole('button', { name: '确认', exact: true }).click(),
      );
      await ui.dialog().waitFor({ state: 'hidden' });
      const response = await api.request(`${config.endpoint}/get?id=${id}`);
      assert.equal(response.body.data[config.property], `${config.value}改`);
      state[config.key].value = `${config.value}改`;
      state[config.key].record = response.body.data;
      await writeFile(
        join(work, 'accounts-state.json'),
        JSON.stringify(state, null, 2),
      );
    });
  }
}
