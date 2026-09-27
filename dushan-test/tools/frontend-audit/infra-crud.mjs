import { writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function runInfraCrud(api) {
  const { page, goto, test, assert, settle, work, server } = api;
  const ui = controls(page, assert);
  const state = {};
  const save = () =>
    writeFile(join(work, 'infra-state.json'), JSON.stringify(state, null, 2));
  const cases = [
    {
      key: 'dataSource',
      title: '数据源',
      path: '/infra/dataSourceConfig',
      endpoint: '/admin-api/infra/data-source',
      label: '数据源名称',
      property: 'name',
      value: 'QA本机MySQL',
      async fill() {
        await ui.fill('数据源名称', 'QA本机MySQL');
        await ui.fill('主机地址', '127.0.0.1');
        await ui.fill('端口', server.mysqlPort);
        await ui.fill('数据库名', server.database);
        await ui.fill('用户名', 'root');
        await ui.fill('连接池大小', 2);
        await ui.fill('最大溢出', 1);
        await ui.fill('备注', '仅隔离测试库');
      },
    },
    {
      key: 'job',
      title: '任务',
      path: '/infra/job',
      endpoint: '/admin-api/infra/job',
      label: '任务名称',
      property: 'name',
      value: 'QA日志清理任务',
      async fill() {
        await ui.fill('任务名称', 'QA日志清理任务');
        await ui.fill('处理器名称', 'infra.job.log.clean');
        await ui.fill('处理器参数', '{}');
        await ui
          .dialog()
          .getByPlaceholder('请输入 CRON 表达式', { exact: true })
          .fill('0 0 1 1 *');
        await ui.fill('监控超时', 60_000);
      },
    },
    {
      key: 'mq',
      title: '消息定义',
      path: '/infra/mq',
      endpoint: '/admin-api/infra/mq',
      label: '描述',
      property: 'description',
      value: 'QA消息定义',
      async fill() {
        await ui.fill('消息主题', 'qa:audit');
        await ui.fill('消费者名称', 'qa.audit');
        await ui.fill('重试次数', 1);
        await ui.fill('描述', 'QA消息定义');
      },
    },
    {
      key: 'fileConfig',
      title: '文件配置',
      path: '/infra/file/config',
      endpoint: '/admin-api/infra/file/config',
      label: '配置名',
      property: 'name',
      value: 'QA数据库存储',
      async fill() {
        await ui.fill('配置名', 'QA数据库存储');
        await ui.select('存储器', '数据库');
        await ui.fill('自定义域名', server.origin);
        await ui.fill('备注', '独立文件测试');
      },
    },
  ];
  for (const config of cases) {
    let id;
    await test(`${config.title}：新增与后端持久化`, async () => {
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
  if (state.dataSource) {
    await test('数据源：实际 MySQL 连接测试', async () => {
      await goto('/infra/dataSourceConfig');
      await ui.rowButton(state.dataSource.id, '更多');
      await page.getByRole('menuitem', { name: '测试', exact: true }).click();
      await settle();
      assert((await page.locator('body').innerText()).includes('连接成功'));
    });
  }
}
