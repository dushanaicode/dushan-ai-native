import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function runDeleteMatrix(api) {
  const { page, goto, test, assert, work, output, settle, server } = api;
  const ui = controls(page, assert);
  const get = async (file) =>
    JSON.parse(await readFile(join(work, `${file}-state.json`), 'utf8'));
  const [core, accounts, content, admin, infra] = await Promise.all(
    ['core', 'accounts', 'content', 'admin', 'infra'].map((file) => get(file)),
  );
  const spec = JSON.parse(await readFile(join(work, 'openapi.json'), 'utf8'));
  const mutations = [];
  const cases = [
    [
      '字典数据',
      '/system/dict',
      '/system/dict/data',
      content.dictData,
      { label: 'QA批量字典', value: 'qa_batch' },
      content.dictType,
      1,
    ],
    [
      '配置数据',
      '/infra/config',
      '/infra/config',
      content.configData,
      { name: 'QA批量配置', key: 'qa.batch.value' },
      content.configType,
      1,
    ],
    [
      '通知',
      '/system/notification/notice',
      '/system/notification',
      content.notice,
      { title: 'QA批量通知' },
    ],
    [
      '公告',
      '/system/announcement',
      '/system/announcement',
      content.announcement,
      { title: 'QA批量公告' },
    ],
    [
      '邮件模板',
      '/system/message/mail/template',
      '/system/mail/template',
      content.mailTemplate,
      { name: 'QA批量模板', code: 'qa_batch_mail' },
    ],
    [
      '用户',
      '/system/user',
      '/system/user',
      accounts.user,
      {
        username: 'qabatchuser',
        nickname: 'QA批量用户',
        password: 'QAtest123',
      },
    ],
    [
      '角色',
      '/system/role',
      '/system/permission/role',
      core.role,
      { name: 'QA批量角色', code: 'qa_batch_role' },
    ],
    [
      '岗位',
      '/system/post',
      '/system/dept/post',
      core.post,
      { name: 'QA批量岗位', code: 'qa_batch_post' },
    ],
    [
      '部门',
      '/system/dept',
      '/system/dept',
      core.dept,
      { name: 'QA批量部门', email: 'qa-dept@example.com' },
    ],
    [
      '字典类型',
      '/system/dict',
      '/system/dict/type',
      content.dictType,
      { name: 'QA批量字典类型', type: 'qa_batch_type' },
    ],
    [
      '配置类型',
      '/infra/config',
      '/infra/config/type',
      content.configType,
      { name: 'QA批量配置类型', code: 'qa_batch_type' },
    ],
    [
      '邮箱账号',
      '/system/message/mail/account',
      '/system/mail/account',
      accounts.mailAccount,
      {
        mail: 'qa-batch@example.com',
        username: 'qa-batch',
        password: 'QAtest123',
      },
    ],
    [
      '短信渠道',
      '/system/message/sms/channel',
      '/system/sms/channel',
      accounts.smsChannel,
      { signature: 'QA批量', apiKey: 'qa-key', apiSecret: 'qa-secret' },
    ],
    [
      '社交客户端',
      '/system/social/client',
      '/system/social/client',
      admin.socialClient,
      {
        name: 'QA批量社交',
        clientId: 'qa-batch-client',
        clientSecret: 'qa-secret',
      },
    ],
    [
      '租户',
      '/system/tenant-manage/tenant',
      '/system/tenant',
      admin.tenant,
      { name: 'QA批量租户', username: 'qabatchtenant', password: 'QAtest123' },
    ],
    [
      '存储配置',
      '/infra/file/config',
      '/infra/file/config',
      infra.fileConfig,
      { name: 'QA批量存储' },
    ],
    [
      '数据源',
      '/infra/dataSourceConfig',
      '/infra/data-source',
      infra.dataSource,
      {
        name: 'QA批量数据源',
        url: `mysql+aiomysql://root@127.0.0.1:${server.mysqlPort}/${server.database}?charset=utf8mb4`,
      },
    ],
    [
      '菜单',
      '/system/menu',
      '/system/permission/menu',
      admin.menu,
      { name: 'QA批量菜单', permission: 'qa:batch:action' },
    ],
  ];
  for (const [
    title,
    path,
    prefix,
    item,
    overrides,
    parent,
    batchIndex = 0,
  ] of cases) {
    if (!item) continue;
    const endpoint = `/admin-api${prefix}`;
    let record = item.record;
    if (!record) {
      await goto(path);
      record = (await api.request(`${endpoint}/get?id=${item.id}`)).body.data;
    }
    const schemaRef = spec.paths[`${endpoint}/create`].post.requestBody.content[
      'application/json'
    ].schema.$ref
      .split('/')
      .at(-1);
    const fields = Object.keys(spec.components.schemas[schemaRef].properties);
    const clone = Object.fromEntries(
      fields
        .filter(
          (field) =>
            field !== 'id' &&
            record[field] !== undefined &&
            record[field] !== null,
        )
        .map((field) => [field, record[field]]),
    );
    Object.assign(clone, overrides);
    const selectPage = async () => {
      await goto(path);
      if (parent) {
        await ui
          .rows(parent.id)
          .getByText(parent.record.name, { exact: true })
          .first()
          .click();
        await settle();
      }
    };
    if (
      spec.paths[`${endpoint}/update-status`]?.put &&
      typeof record.status === 'number'
    ) {
      await selectPage();
      if (await ui.rows(item.id).locator('.el-switch').count()) {
        await test(`${title}：状态关闭和恢复`, async () => {
          for (const status of [record.status === 1 ? 0 : 1, record.status]) {
            await ui.rows(item.id).locator('.el-switch').last().click();
            await ui.responseDuring(
              `${endpoint}/update-status`,
              'PUT',
              ui.confirm,
            );
            await page.getByRole('alertdialog').waitFor({ state: 'hidden' });
            await settle();
            assert.equal(
              (await api.request(`${endpoint}/get?id=${item.id}`)).body.data
                .status,
              status,
            );
          }
        });
      }
    }
    let removed = false;
    await test(`${title}：单条删除与列表更新`, async () => {
      await selectPage();
      await ui.rowButton(item.id, '删除');
      await ui.responseDuring(`${endpoint}/delete`, 'DELETE', () =>
        page
          .locator('.el-popconfirm:visible')
          .getByRole('button', { name: '确定', exact: true })
          .click(),
      );
      await settle();
      assert.equal(await ui.rows(item.id).count(), 0);
      removed = true;
      mutations.push({ title, action: 'delete', id: item.id });
    });
    if (!removed) continue;
    let id;
    await test(`${title}：批量删除的隔离数据准备`, async () => {
      const response = await api.request(`${endpoint}/create`, {
        method: 'POST',
        data: clone,
      });
      assert.equal(response.body.code, 0);
      id = response.body.data;
      mutations.push({ title, action: 'browser-api-fixture', id });
    });
    if (!id) continue;
    const deleted = await test(`${title}：勾选后批量删除`, async () => {
      await selectPage();
      await page.reload();
      await settle();
      if (parent) {
        await ui
          .rows(parent.id)
          .getByText(parent.record.name, { exact: true })
          .first()
          .click();
        await settle();
      }
      await ui.rows(id).locator('.vxe-cell--checkbox').last().click();
      await ui
        .main()
        .getByRole('button', { name: '批量删除', exact: true })
        .nth(batchIndex)
        .click();
      await ui.responseDuring(`${endpoint}/delete-list`, 'DELETE', () =>
        page
          .locator('.el-popconfirm:visible')
          .getByRole('button', { name: '确定', exact: true })
          .click(),
      );
      await settle();
      assert.equal(await ui.rows(id).count(), 0);
      mutations.push({ title, action: 'delete-list', id });
    });
    if (deleted.status === 'failed') {
      const cleanup = await api.request(`${endpoint}/delete?id=${id}`, {
        method: 'DELETE',
      });
      mutations.push({
        title,
        action: 'fixture-cleanup-after-failed-ui',
        id,
        code: cleanup.body.code,
      });
    }
    await writeFile(
      join(output, 'mutation-ledger.json'),
      JSON.stringify(mutations, null, 2),
    );
  }
}
