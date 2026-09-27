import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function runContentCrud(api) {
  const { page, goto, test, assert, settle, work } = api;
  const ui = controls(page, assert);
  const accounts = JSON.parse(
    await readFile(join(work, 'accounts-state.json'), 'utf8'),
  );
  const state = {};
  const key = Date.now().toString(36).slice(-6);
  const rich = async (value) => {
    await ui.dialog().locator('[contenteditable="true"]').fill(value);
    await page.keyboard.press('Tab');
  };
  const cases = [
    {
      key: 'dictType',
      title: '字典类型',
      path: '/system/dict',
      endpoint: '/admin-api/system/dict/type',
      label: '字典名称',
      property: 'name',
      fill: async () => {
        await ui.fill('字典名称', `QA字典${key}`);
        await ui.fill('字典类型', `qa_dict_${key}`);
        await ui.fill('备注', '浏览器字典测试');
      },
    },
    {
      key: 'configType',
      title: '配置类型',
      path: '/infra/config',
      endpoint: '/admin-api/infra/config/type',
      label: '类型名称',
      property: 'name',
      fill: async () => {
        await ui.fill('类型名称', `QA配置${key}`);
        await ui.fill('类型编码', `qa_config_${key}`);
        await ui.fill('备注', '浏览器配置测试');
      },
    },
    {
      key: 'mailTemplate',
      title: '邮件模板',
      path: '/system/message/mail/template',
      endpoint: '/admin-api/system/mail/template',
      label: '模板名称',
      property: 'name',
      fill: async () => {
        await ui.fill('模板名称', `QA邮件${key}`);
        await ui.fill('模板编码', `qa_mail_${key}`);
        await ui.select('邮箱账号', accounts.mailAccount.record.mail);
        await ui.fill('发件人名称', 'QA自动化');
        await ui.fill('邮件标题', `QA邮件${key}`);
        await ui.fill('模板参数', 'code');
        await rich('测试验证码 {code}');
      },
    },
    {
      key: 'smsTemplate',
      title: '短信模板',
      path: '/system/message/sms/template',
      endpoint: '/admin-api/system/sms/template',
      label: '模板名称',
      property: 'name',
      fill: async () => {
        await ui.fill('模板名称', `QA短信${key}`);
        await ui.fill('模板编码', `qa_sms_${key}`);
        await ui.select('短信类型', '验证码');
        await ui.select('短信渠道', accounts.smsChannel.record.signature);
        await ui.fill('API 模板编号', 'QA_TEMPLATE');
        await ui.fill('模板内容', '测试 {code}');
      },
    },
    {
      key: 'announcement',
      title: '公告',
      path: '/system/announcement',
      endpoint: '/admin-api/system/announcement',
      label: '公告标题',
      property: 'title',
      fill: async () => {
        await ui.fill('公告标题', `QA公告${key}`);
        await ui.select('公告类别', '通知');
        await ui.fill('发布人', 'QA自动化');
        await rich('浏览器公告测试内容');
      },
    },
    {
      key: 'notice',
      title: '通知',
      path: '/system/notification/notice',
      endpoint: '/admin-api/system/notification',
      label: '通知标题',
      property: 'title',
      fill: async () => {
        await ui.fill('通知标题', `QA通知${key}`);
        await ui.select('通知类型', '系统通知');
        await ui.select('用户类型', '管理员');
        await ui.select('推送渠道', '站内信');
        await page.keyboard.press('Escape');
        await ui.fill('发布人', 'QA自动化');
        await rich('浏览器站内信测试内容');
      },
    },
  ];
  for (const config of cases) {
    let id;
    await test(`${config.title}：新增与数据核验`, async () => {
      await goto(config.path);
      id = await ui.create(`新增${config.title}`, config.endpoint, config.fill);
      await settle();
      const { body } = await api.request(`${config.endpoint}/get?id=${id}`);
      assert.equal(body.code, 0);
      state[config.key] = { id, record: body.data };
      await writeFile(
        join(work, 'content-state.json'),
        JSON.stringify(state, null, 2),
      );
      return { id };
    });
    if (!id) continue;
    await test(`${config.title}：编辑与回填`, async () => {
      await goto(config.path);
      await ui.rowButton(id, '修改');
      await settle();
      const changed = `${state[config.key].record[config.property]}改`;
      await ui.fill(config.label, changed);
      await ui.responseDuring(`${config.endpoint}/update`, 'PUT', () =>
        ui.dialog().getByRole('button', { name: '确认', exact: true }).click(),
      );
      await ui.dialog().waitFor({ state: 'hidden' });
      const { body } = await api.request(`${config.endpoint}/get?id=${id}`);
      assert.equal(body.data[config.property], changed);
      state[config.key].record = body.data;
      await writeFile(
        join(work, 'content-state.json'),
        JSON.stringify(state, null, 2),
      );
    });
  }
  await test('租户套餐菜单树：核对非空接口与空白选择区', async () => {
    await goto('/system/tenant-manage/tenantPackage');
    const menus = await api.request(
      '/admin-api/system/permission/menu/simple-list',
    );
    assert.equal(menus.body.code, 0);
    await ui
      .main()
      .getByRole('button', { name: '新增租户套餐', exact: true })
      .click();
    await settle();
    const snapshot = await ui.dialog().ariaSnapshot();
    await writeFile(join(api.output, 'tenant-tree.txt'), snapshot);
    assert(menus.body.data.length > 0, '后端菜单列表为空');
    assert(
      !snapshot.includes('暂无数据'),
      `后端有 ${menus.body.data.length} 项菜单，但表单选择区显示暂无数据`,
    );
  });
}
