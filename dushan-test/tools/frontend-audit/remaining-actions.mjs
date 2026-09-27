import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function runRemainingActions(api) {
  const { page, goto, test, assert, work, output, server, settle } = api;
  const ui = controls(page, assert);
  const state = JSON.parse(
    await readFile(join(work, 'infra-state.json'), 'utf8'),
  );
  const spec = JSON.parse(await readFile(join(work, 'openapi.json'), 'utf8'));
  const project = (value, schema) =>
    Object.fromEntries(
      Object.keys(spec.components.schemas[schema].properties)
        .filter((key) => key in value)
        .map((key) => [key, value[key]]),
    );
  let sourceId;
  await test('数据源 API：为代码生成补充操作准备有效连接', async () => {
    await goto('/infra/dataSourceConfig');
    const response = await api.request('/admin-api/infra/data-source/create', {
      method: 'POST',
      data: {
        name: 'QA补充验证源',
        dbType: 'mysql',
        url: `mysql+aiomysql://root@127.0.0.1:${server.mysqlPort}/${server.database}?charset=utf8mb4`,
        sourceType: 1,
        status: 1,
        isDefault: false,
        echo: false,
        poolSize: 2,
        maxOverflow: 1,
        poolRecycle: 3600,
        poolTimeout: 30,
      },
    });
    assert.equal(response.body.code, 0);
    sourceId = response.body.data;
  });
  if (sourceId) {
    await test('代码生成 API：编辑数据与同步，验证路由阻塞之外的接口', async () => {
      const detail = (
        await api.request(
          `/admin-api/infra/codegen/detail?tableId=${state.codegen.id}`,
        )
      ).body.data;
      const table = project(detail.table, 'CodegenTableUpdateReqVO');
      table.dataSourceConfigId = sourceId;
      table.remark = 'QA 补充编辑';
      const columns = detail.columns.map((column) =>
        project(column, 'CodegenColumnUpdateReqVO'),
      );
      const response = await api.request('/admin-api/infra/codegen/update', {
        method: 'PUT',
        data: { table, columns },
      });
      assert.equal(response.body.code, 0);
      await goto('/infra/codegen');
      await ui.rowButton(state.codegen.id, '更多');
      await page.getByRole('menuitem', { name: '同步', exact: true }).click();
      await ui.responseDuring(
        '/admin-api/infra/codegen/sync-from-db',
        'PUT',
        () =>
          page
            .locator('.el-popconfirm:visible')
            .getByRole('button', { name: '确定', exact: true })
            .click(),
      );
    });
    await test('代码生成：批量删除导入的元数据', async () => {
      await goto('/infra/codegen');
      await ui
        .rows(state.codegen.id)
        .locator('.vxe-cell--checkbox')
        .last()
        .click();
      await ui
        .main()
        .getByRole('button', { name: '批量删除', exact: true })
        .click();
      await ui.responseDuring(
        '/admin-api/infra/codegen/delete-list',
        'DELETE',
        () =>
          page
            .locator('.el-popconfirm:visible')
            .getByRole('button', { name: '确定', exact: true })
            .click(),
      );
    });
    await test('数据源 API：无 UI 入口的批量删除', async () => {
      assert.equal(
        (
          await api.request(
            `/admin-api/infra/data-source/delete-list?ids=${sourceId}`,
            {
              method: 'DELETE',
            },
          )
        ).body.code,
        0,
      );
    });
  }
  for (const config of [
    {
      title: '任务',
      path: '/infra/job',
      prefix: '/admin-api/infra/job',
      match: (row) => row.handlerName === 'infra.job.log.clean',
      button: '新增任务',
      async fill() {
        await ui.fill('任务名称', 'QA重建任务');
        await ui.fill('处理器名称', 'infra.job.log.clean');
        await ui.fill('处理器参数', '{}');
        await ui
          .dialog()
          .getByPlaceholder('请输入 CRON 表达式')
          .fill('0 0 1 1 *');
        await ui.fill('监控超时', 60_000);
      },
    },
    {
      title: 'MQ定义',
      path: '/infra/mq',
      prefix: '/admin-api/infra/mq',
      match: (row) => row.consumer === 'system.sms.send',
      button: '新增消息定义',
      async fill() {
        await ui.fill('消息主题', 'sms:send');
        await ui.fill('消费者名称', 'system.sms.send');
        await ui.fill('重试次数', 3);
        await ui.fill('描述', 'QA注册消费者重建');
      },
    },
  ]) {
    let id;
    await test(`${config.title}：删除隔离种子并使用真实处理器重新新增`, async () => {
      await goto(config.path);
      const rows = (
        await api.request(`${config.prefix}/page?page=1&pageSize=20`)
      ).body.data.items;
      const row = rows.find((item) => config.match(item));
      assert(row);
      await ui.rowButton(row.id, '删除');
      await ui.responseDuring(`${config.prefix}/delete`, 'DELETE', () =>
        page
          .locator('.el-popconfirm:visible')
          .getByRole('button', { name: '确定', exact: true })
          .click(),
      );
      await settle();
      id = await ui.create(config.button, config.prefix, config.fill);
      await settle();
      assert(id);
    });
    if (!id) continue;
    await test(`${config.title}：修改和批量删除`, async () => {
      await ui.rowButton(id, '修改');
      await settle();
      await ui.fill(
        config.title === '任务' ? '任务名称' : '描述',
        'QA更新验证',
      );
      await ui.responseDuring(`${config.prefix}/update`, 'PUT', () =>
        ui.dialog().getByRole('button', { name: '确认', exact: true }).click(),
      );
      await ui.dialog().waitFor({ state: 'hidden' });
      await settle();
      await ui.rows(id).locator('.vxe-cell--checkbox').last().click();
      await ui
        .main()
        .getByRole('button', { name: '批量删除', exact: true })
        .click();
      await ui.responseDuring(
        config.prefix +
          (config.title === 'MQ定义' ? '/delete' : '/delete-list'),
        'DELETE',
        () =>
          page
            .locator('.el-popconfirm:visible')
            .getByRole('button', { name: '确定', exact: true })
            .click(),
      );
    });
  }
  await test('任务同步：刷新现有定义且不复活已删除任务', async () => {
    await goto('/infra/job');
    await ui
      .main()
      .getByRole('button', { name: '同步任务', exact: true })
      .click();
    await page
      .locator('.el-popconfirm:visible')
      .getByRole('button', { name: '确定', exact: true })
      .click();
    await settle();
    const jobs = (
      await api.request('/admin-api/infra/job/page?page=1&pageSize=20')
    ).body.data.items;
    assert(!jobs.some((job) => job.handlerName === 'infra.job.log.clean'));
  });
  await test('租户套餐：API 准备后测试删除操作', async () => {
    await goto('/system/tenant-manage/tenantPackage');
    const menu = (await api.request('/admin-api/system/permission/menu/list'))
      .body.data[0];
    const created = await api.request(
      '/admin-api/system/tenant/package/create',
      {
        method: 'POST',
        data: { name: 'QA删除套餐', status: 1, menuIds: [menu.id] },
      },
    );
    assert.equal(created.body.code, 0);
    await page.reload();
    await settle();
    await ui
      .rows(created.body.data)
      .locator('.vxe-cell--checkbox')
      .last()
      .click();
    await ui
      .main()
      .getByRole('button', { name: '批量删除', exact: true })
      .click();
    await ui.responseDuring(
      '/admin-api/system/tenant/package/delete-list',
      'DELETE',
      () =>
        page
          .locator('.el-popconfirm:visible')
          .getByRole('button', { name: '确定', exact: true })
          .click(),
    );
  });
  await test('扫码登录：记录当前演示二维码入口', async () => {
    const actor = await api.context.browser().newContext();
    try {
      const tab = await actor.newPage();
      await tab.goto(`${server.origin}/#/auth/login`);
      await tab.getByRole('button', { name: '扫码登录', exact: true }).click();
      await tab.getByRole('img', { name: 'qrcode' }).waitFor();
      await tab.screenshot({ path: join(output, 'qr-demo.png') });
      await writeFile(
        join(output, 'qr-demo.txt'),
        await tab.locator('body').ariaSnapshot(),
      );
      const source = await readFile(
        'dushan-admin-frontend/packages/effects/common-ui/src/ui/authentication/qrcode-login.vue',
        'utf8',
      );
      assert(
        !source.includes("ref('https://vben.vvbin.cn')"),
        '扫码登录仍是 Vben 官网固定二维码，没有 Native 登录票据或轮询',
      );
    } finally {
      await actor.close();
    }
  });
}
