import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function runUtilityUi(api) {
  const { page, goto, test, assert, settle, work, output } = api;
  const ui = controls(page, assert);
  const state = JSON.parse(
    await readFile(join(work, 'infra-state.json'), 'utf8'),
  );
  await test('存储配置：菜单中测试读写与查看结果', async () => {
    await goto('/infra/file/config');
    await ui.rowButton(state.fileConfig.id, '更多');
    await page.getByRole('menuitem', { name: '测试', exact: true }).click();
    await settle();
    const dialog = page.getByRole('alertdialog');
    await dialog.waitFor();
    await writeFile(
      join(output, 'storage-test.txt'),
      await dialog.ariaSnapshot(),
    );
    await dialog.getByRole('button', { name: '取消', exact: true }).click();
  });
  await test('存储配置：切换主配置并还原', async () => {
    await goto('/infra/file/config');
    for (const id of [state.fileConfig.id, '10300000040001']) {
      await ui.rowButton(id, '更多');
      await page
        .getByRole('menuitem', { name: '设为主配置', exact: true })
        .click();
      await page
        .locator('.el-popconfirm:visible')
        .getByRole('button', { name: '确定', exact: true })
        .click();
      await settle();
      assert.equal(
        (await api.request(`/admin-api/infra/file/config/get?id=${id}`)).body
          .data.master,
        true,
      );
    }
  });
  await test('任务状态：逐次等待确认完成并验证持久化', async () => {
    await goto('/infra/job');
    const jobs = (
      await api.request('/admin-api/infra/job/page?page=1&pageSize=20')
    ).body.data.items;
    const job = jobs.find((item) => item.handlerName === 'infra.job.log.clean');
    const expected = job.status === 1 ? [2, 1] : [1, 2, 1];
    for (const status of expected) {
      await ui.rows(job.id).locator('.el-switch').last().click();
      await ui.responseDuring(
        '/admin-api/infra/job/update-status',
        'PUT',
        ui.confirm,
      );
      await page.getByRole('alertdialog').waitFor({ state: 'hidden' });
      await settle();
      assert.equal(
        (await api.request(`/admin-api/infra/job/get?id=${job.id}`)).body.data
          .status,
        status,
      );
    }
    state.job = { id: job.id, record: job };
    await writeFile(
      join(work, 'infra-state.json'),
      JSON.stringify(state, null, 2),
    );
  });
  if (state.job) {
    await test('任务：立即执行并查询实际日志', async () => {
      await goto('/infra/job');
      await ui.rowButton(state.job.id, '更多');
      await page
        .getByRole('menuitem', { name: '执行一次', exact: true })
        .click();
      await page
        .locator('.el-popconfirm:visible')
        .getByRole('button', { name: '确定', exact: true })
        .click();
      await settle();
      await ui.rowButton(state.job.id, '更多');
      await page
        .getByRole('menuitem', { name: '执行日志', exact: true })
        .click();
      await settle();
      await writeFile(
        join(output, 'job-log.txt'),
        await ui.main().ariaSnapshot(),
      );
      const logs = await api.request(
        `/admin-api/infra/job/log/page?page=1&pageSize=20&jobId=${state.job.id}`,
      );
      assert.equal(logs.body.code, 0);
      assert(logs.body.data.total > 0, '立即执行后未产生任务日志');
    });
  }
  await test('代码生成：编辑向导保存', async () => {
    await goto('/infra/codegen');
    await ui.rowButton(state.codegen.id, '修改');
    await ui
      .main()
      .getByRole('textbox', { name: '备注', exact: true })
      .fill('完整浏览器验收');
    await ui
      .main()
      .getByRole('button', { name: '下一步', exact: true })
      .click();
    await ui
      .main()
      .getByRole('button', { name: '下一步', exact: true })
      .click();
    await ui.responseDuring('/admin-api/infra/codegen/update', 'PUT', () =>
      ui.main().getByRole('button', { name: '保存', exact: true }).click(),
    );
    await settle();
  });
  await test('代码生成：ZIP 下载与同步结构', async () => {
    await goto('/infra/codegen');
    await ui.rowButton(state.codegen.id, '更多');
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('menuitem', { name: '生成代码', exact: true }).click(),
    ]);
    await download.saveAs(join(output, 'codegen.zip'));
    assert.equal(
      (await readFile(join(output, 'codegen.zip'))).subarray(0, 2).toString(),
      'PK',
    );
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
  await test('表单构建：导入 JSON、预览与生成 Vue 文件', async () => {
    await goto('/infra/build');
    await ui
      .main()
      .getByRole('button', { name: '导入 JSON', exact: true })
      .click();
    await ui
      .dialog()
      .getByRole('textbox')
      .fill(
        JSON.stringify([
          {
            type: 'input',
            field: 'qaName',
            title: 'QA姓名',
            value: '测试用户',
            props: { placeholder: '请输入姓名' },
            validate: [{ required: true, message: '姓名必填' }],
          },
        ]),
      );
    await ui
      .dialog()
      .getByRole('button', { name: '导入', exact: true })
      .click();
    await ui.dialog().waitFor({ state: 'hidden' });
    await ui
      .main()
      .getByRole('button', { name: /预览$/ })
      .click();
    await ui.dialog().waitFor();
    assert((await ui.dialog().innerText()).includes('QA姓名'));
    await ui
      .dialog()
      .getByRole('button', { name: /关闭|Close/ })
      .click();
    await ui
      .main()
      .getByRole('button', { name: '生成 Vue 组件', exact: true })
      .click();
    await ui.dialog().waitFor();
    assert((await ui.dialog().locator('code').innerText()).includes('qaName'));
    await writeFile(
      join(output, 'GeneratedForm.vue'),
      await ui.dialog().locator('code').innerText(),
    );
    await ui.close();
  });
  await test('API 文档：实际 Swagger 与 ReDoc 内页', async () => {
    await goto('/infra/docs');
    const frame = page.frameLocator('iframe');
    await frame.locator('.swagger-ui').waitFor({ timeout: 20_000 });
    await frame
      .getByRole('link', { name: '/admin-api/system/user/page', exact: true })
      .first()
      .waitFor({ timeout: 20_000 });
    assert(
      (await frame.locator('body').innerText()).includes(
        '/admin-api/system/user/page',
      ),
    );
    await ui.main().getByText('ReDoc', { exact: true }).click();
    await frame.locator('.redoc-wrap').waitFor({ timeout: 20_000 });
    await frame
      .getByText('System - 用户管理', { exact: false })
      .first()
      .waitFor({ timeout: 20_000 });
    assert((await frame.locator('body').innerText()).includes('用户管理'));
  });
}
