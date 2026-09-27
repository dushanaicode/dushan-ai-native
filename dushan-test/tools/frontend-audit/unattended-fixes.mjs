import { Buffer } from 'node:buffer';
import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function run(api) {
  const { page, server, assert, test, goto, settle, work, output } = api;
  assert.notEqual(server.apiPort, 48_080);
  assert.notEqual(new URL(server.origin).port, '5777');
  const ui = controls(page, assert);
  const suffix = Date.now().toString(36).slice(-6);
  await api.login();
  const create = async (endpoint, data) => {
    const result = await api.request(`${endpoint}/create`, {
      method: 'POST',
      data,
    });
    assert.equal(result.body.code, 0);
    return result.body.data;
  };
  const save = async (endpoint) => {
    const result = await ui.responseDuring(`${endpoint}/update`, 'PUT', () =>
      ui.dialog().getByRole('button', { name: '确认', exact: true }).click(),
    );
    await ui.dialog().waitFor({ state: 'hidden' });
    await settle();
    return result;
  };

  await test('F01 部门空邮箱新增、编辑、清空', async () => {
    const endpoint = '/admin-api/system/dept';
    await goto('/system/dept');
    const id = await ui.create('新增部门', endpoint, async () => {
      await ui.select('上级部门', '顶级部门');
      await ui.fill('部门名称', `QA部门${suffix}`);
      await ui.fill('显示顺序', 1);
      await settle();
    });
    await settle();
    for (const email of ['qa@example.com', '']) {
      await ui.rowButton(id, '修改');
      await settle();
      await ui.fill('邮箱', email);
      await save(endpoint);
    }
    assert.equal(
      (await api.request(`${endpoint}/get?id=${id}`)).body.data.email,
      null,
    );
  });

  const credentials = [
    {
      title: 'F02 邮箱',
      path: '/system/message/mail/account',
      endpoint: '/admin-api/system/mail/account',
      label: '用户名',
      field: 'username',
      secretLabel: '密码',
      data: {
        mail: 'qa@example.com',
        username: `qa${suffix}`,
        password: 'QA-Original123!',
        host: '127.0.0.1',
        port: server.smtpPort,
        sslEnable: false,
        starttlsEnable: false,
      },
    },
    {
      title: 'F03 短信',
      path: '/system/message/sms/channel',
      endpoint: '/admin-api/system/sms/channel',
      label: '备注',
      field: 'remark',
      secretLabel: 'API 账号',
      data: {
        signature: `QA${suffix}`,
        code: 'ALIYUN',
        apiKey: 'qa-api-key',
        apiSecret: 'qa-api-secret',
        status: 0,
        remark: 'before',
      },
    },
    {
      title: 'F04 社交',
      path: '/system/social/client',
      endpoint: '/admin-api/system/social/client',
      label: '应用名',
      field: 'name',
      secretLabel: '密钥 / 私钥',
      data: {
        name: `QA社交${suffix}`,
        socialType: 20,
        userType: 2,
        clientId: `qa${suffix}`,
        clientSecret: 'qa-client-secret',
        status: 0,
      },
    },
  ];
  for (const config of credentials) {
    await test(`${config.title}脱敏编辑不必重填凭据`, async () => {
      let id;
      if (config.title.startsWith('F04')) {
        const existing = await api.request(
          `${config.endpoint}/page?socialType=20&userType=2`,
        );
        assert.equal(existing.body.code, 0);
        id = existing.body.data.items[0]?.id;
      }
      id ??= await create(config.endpoint, config.data);
      await goto(config.path);
      await ui.rowButton(id, '修改');
      await settle();
      assert.equal(
        await ui
          .dialog()
          .getByLabel(new RegExp(`${config.secretLabel}$`))
          .inputValue(),
        '',
      );
      const changed = `QA修改${suffix}`;
      await ui.fill(config.label, changed);
      await save(config.endpoint);
      const result = (await api.request(`${config.endpoint}/get?id=${id}`))
        .body;
      assert.equal(result.code, 0);
      assert.equal(result.data[config.field], changed);
      assert.ok(!JSON.stringify(result.data).includes('qa-client-secret'));
    });
  }

  await test('F07 套餐菜单树勾选保存、重开与雪花字符串', async () => {
    const endpoint = '/admin-api/system/tenant/package';
    await goto('/system/tenant-manage/tenantPackage');
    const id = await ui.create('新增租户套餐', endpoint, async () => {
      await ui.fill('套餐名称', `QA套餐${suffix}`);
      await ui
        .dialog()
        .getByRole('treeitem')
        .first()
        .getByRole('checkbox')
        .first()
        .click();
    });
    await settle();
    const original = (await api.request(`${endpoint}/get?id=${id}`)).body.data
      .menuIds;
    assert.ok(
      original.length > 0 &&
        original.every((value) => typeof value === 'string'),
    );
    await ui.rowButton(id, '修改');
    await settle();
    assert.ok(
      await ui.dialog().getByRole('checkbox', { checked: true }).count(),
    );
    await save(endpoint);
    const reopened = (await api.request(`${endpoint}/get?id=${id}`)).body.data
      .menuIds;
    assert.deepEqual(reopened.toSorted(), original.toSorted());
  });

  await test('F09 F13 用户导入模板通过浏览器实际保存', async () => {
    await goto('/system/user');
    await ui.main().getByRole('button', { name: '导入', exact: true }).click();
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      ui
        .dialog()
        .getByRole('button', { name: '下载模板', exact: true })
        .click(),
    ]);
    assert.ok(download.suggestedFilename().endsWith('.xlsx'));
    const destination = join(output, download.suggestedFilename());
    await download.saveAs(destination);
    assert.equal((await readFile(destination)).subarray(0, 2).toString(), 'PK');
    await ui.close();
  });
  await test('F10 F17 无效文件拒绝与替换后真实导入', async () => {
    await goto('/system/user');
    await ui.main().getByRole('button', { name: '导入', exact: true }).click();
    let requests = 0;
    const count = (request) => {
      if (new URL(request.url()).pathname === '/admin-api/system/user/import')
        requests++;
    };
    page.on('request', count);
    try {
      const input = ui.dialog().locator('input[type="file"]');
      await input.setInputFiles({
        name: 'invalid.txt',
        mimeType: 'text/plain',
        buffer: Buffer.from('invalid'),
      });
      await ui
        .dialog()
        .getByRole('button', { name: '确认导入', exact: true })
        .click();
      await settle();
      assert.equal(requests, 0);
      await input.setInputFiles(join(work, 'user-import.xlsx'));
      await input.setInputFiles(join(work, 'user-import-replacement.xlsx'));
      const imported = await ui.responseDuring(
        '/admin-api/system/user/import',
        'POST',
        () =>
          ui
            .dialog()
            .getByRole('button', { name: '确认导入', exact: true })
            .click(),
      );
      assert.deepEqual(imported.createUsernames, ['qareplaced']);
      assert.equal(requests, 1);
      assert.ok((await ui.dialog().innerText()).includes('新增 1 个'));
    } finally {
      page.off('request', count);
      await ui.close();
    }
  });

  await test('F11 F18 OAuth 图标上传、编辑留空密钥与重开预览', async () => {
    const endpoint = '/admin-api/system/oauth2/client';
    const id = await create(endpoint, {
      clientId: `qa${suffix}`,
      name: `QA客户端${suffix}`,
      secret: 'QA-Original-Client-Secret-123456789!',
      logo: `${server.origin}/favicon.ico`,
      status: 1,
      userType: 2,
      accessTokenValiditySeconds: 1800,
      refreshTokenValiditySeconds: 2_592_000,
      redirectUris: [`${server.origin}/callback`],
      authorizedGrantTypes: ['authorization_code', 'refresh_token'],
      scopes: [],
      autoApproveScopes: [],
      authorities: [],
      resourceIds: [],
    });
    const logo = join(output, 'logo.png');
    await writeFile(
      logo,
      Buffer.from(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aC1cAAAAASUVORK5CYII=',
        'base64',
      ),
    );
    await goto('/system/oauth2/client');
    await ui.rowButton(id, '修改');
    await settle();
    assert.equal(
      await ui
        .dialog()
        .getByLabel(/客户端密钥$/)
        .inputValue(),
      '',
    );
    await ui
      .dialog()
      .getByRole('button', { name: '移除', exact: true })
      .click();
    await ui.responseDuring('/admin-api/infra/file/upload', 'POST', () =>
      ui.dialog().locator('input[type="file"]').setInputFiles(logo),
    );
    await settle();
    await ui.fill('客户端名称', `QA上传${suffix}`);
    await save(endpoint);
    const record = (await api.request(`${endpoint}/get?id=${id}`)).body.data;
    assert.ok(
      record.logo.startsWith(server.origin) &&
        record.logo.includes('/admin-api/infra/file/'),
    );
    await ui.rowButton(id, '修改');
    await settle();
    assert.ok(await ui.dialog().locator(`img[src="${record.logo}"]`).count());
    await ui.close();
  });

  for (const path of [
    '/infra/job',
    '/infra/mq',
    '/infra/dataSourceConfig',
    '/infra/api-log/access',
    '/infra/api-log/error',
  ]) {
    await test(`F08 F13 ${path} 导出并实际下载 XLSX`, async () => {
      await goto(path);
      await ui
        .main()
        .getByRole('button', { name: '导出', exact: true })
        .click();
      await ui.dialog().waitFor();
      const [download] = await Promise.all([
        page.waitForEvent('download'),
        ui
          .dialog()
          .getByRole('button', { name: /导出/ })
          .click(),
      ]);
      assert.ok(download.suggestedFilename().endsWith('.xlsx'));
      const file = join(
        output,
        `${path.replaceAll('/', '-')}-${download.suggestedFilename()}`,
      );
      await download.saveAs(file);
      assert.equal((await readFile(file)).subarray(0, 2).toString(), 'PK');
    });
  }

  await test('F12 MQ 只能选择已部署消费者，主题和重试自动回填', async () => {
    await goto('/infra/mq');
    await ui
      .main()
      .getByRole('button', { name: '新增消息定义', exact: true })
      .click();
    const declarations = (await api.request('/admin-api/infra/mq/consumers'))
      .body.data;
    const selected = declarations[0];
    await ui.select('消费者名称', selected.key);
    assert.equal(
      await ui
        .dialog()
        .getByLabel(/消息主题$/)
        .inputValue(),
      selected.topic,
    );
    await ui.close();
  });

  await test('F14 存储测试成功后遮罩关闭且取消可点击', async () => {
    await goto('/infra/file/config');
    const row = (
      await api.request('/admin-api/infra/file/config/page')
    ).body.data.items.find((item) => item.master);
    await ui.rowButton(row.id, '更多');
    await page.getByRole('menuitem', { name: '测试', exact: true }).click();
    await page
      .getByText('测试上传成功，是否访问该文件？', { exact: true })
      .waitFor();
    await page
      .locator('.el-loading-mask.is-fullscreen')
      .waitFor({ state: 'hidden' });
    await page
      .getByRole('button', { name: '取消', exact: true })
      .last()
      .click();
    await settle();
    assert.ok(page.url().includes('/infra/file/config'));
  });

  for (const [path, label] of [
    ['/infra/job', '执行日志'],
    ['/infra/mq', '消费日志'],
  ]) {
    await test(`F15 ${label} 点击与刷新直达`, async () => {
      await goto(path);
      await ui.main().getByRole('button', { name: label, exact: true }).click();
      await page.waitForURL((url) => url.hash.split('?')[0] === `#${path}/log`);
      await page.reload();
      await ui.main().waitFor();
      await settle();
      assert.ok((await ui.main().innerText()).includes('日志'));
    });
  }

  await test('F15 代码生成编辑点击与刷新回填', async () => {
    const source = await create('/admin-api/infra/data-source', {
      name: `QA${suffix}`,
      url: `mysql+aiomysql://root@127.0.0.1:${server.mysqlPort}/${server.database}?charset=utf8mb4`,
      status: 1,
      dbType: 'mysql',
      sourceType: 1,
      isDefault: false,
    });
    const imported = await api.request('/admin-api/infra/codegen/create-list', {
      method: 'POST',
      data: { dataSourceConfigId: source, tableNames: ['qa_codegen_record'] },
    });
    assert.equal(imported.body.code, 0);
    const id = imported.body.data[0];
    await goto('/infra/codegen');
    await ui.rowButton(id, '修改');
    await page.waitForURL((url) =>
      url.hash.includes(`/infra/codegen/edit?id=${id}`),
    );
    await settle();
    await page.reload();
    await ui.main().waitFor();
    await settle();
    assert.ok((await ui.main().innerText()).includes('基本信息'));
  });

  await test('D02 作者清理入口、低风险清理与整库清空取消', async () => {
    await goto('/infra/monitor/redis-cache');
    await ui
      .main()
      .getByRole('button', { name: '清空全部', exact: true })
      .click();
    await page
      .getByRole('button', { name: '取消', exact: true })
      .last()
      .click();
    await ui
      .main()
      .getByRole('button', { name: '清理可重建缓存', exact: true })
      .click();
    await ui.responseDuring(
      '/admin-api/infra/cache/monitor/cleanup-preset',
      'POST',
      () =>
        page.getByRole('button', { name: '清理', exact: true }).last().click(),
    );
    await settle();
  });

  await test('V05 代码生成 ZIP 通过浏览器实际保存', async () => {
    const response = await api.request('/admin-api/infra/codegen/table/page');
    assert.equal(response.body.code, 0);
    const record = response.body.data.items.find(
      (item) => item.tableName === 'qa_codegen_record',
    );
    assert.ok(record);
    await goto('/infra/codegen');
    await ui.rowButton(record.id, '更多');
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('menuitem', { name: '生成代码', exact: true }).click(),
    ]);
    assert.ok(download.suggestedFilename().endsWith('.zip'));
    const target = join(output, download.suggestedFilename());
    await download.saveAs(target);
    assert.equal((await readFile(target)).subarray(0, 2).toString(), 'PK');
  });
}
