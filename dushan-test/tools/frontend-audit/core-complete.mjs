import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function runCoreComplete(api) {
  const { page, goto, test, assert, settle, work, output } = api;
  const ui = controls(page, assert);
  const state = JSON.parse(
    await readFile(join(work, 'core-state.json'), 'utf8'),
  );
  const configs = [
    {
      key: 'post',
      label: '岗位',
      path: '/system/post',
      endpoint: '/admin-api/system/dept/post',
      nameLabel: '岗位名称',
    },
    {
      key: 'role',
      label: '角色',
      path: '/system/role',
      endpoint: '/admin-api/system/permission/role',
      nameLabel: '角色名称',
    },
    {
      key: 'dept',
      label: '部门',
      path: '/system/dept',
      endpoint: '/admin-api/system/dept',
      nameLabel: '部门名称',
    },
  ];
  for (const config of configs) {
    const { id, name } = state[config.key];
    await test(`${config.label}：开关鼠标操作及确认`, async () => {
      await goto(config.path);
      await ui.search(config.nameLabel, name);
      await settle();
      const control = ui.rows(id).locator('.el-switch').last();
      await writeFile(
        join(output, `${config.key}-switch.html`),
        await control.evaluate((node) => node.outerHTML),
      );
      await control.click();
      await writeFile(
        join(output, `${config.key}-confirmation.txt`),
        await page.locator('body').ariaSnapshot(),
      );
      await ui.responseDuring(`${config.endpoint}/update-status`, 'PUT', () =>
        ui.confirm(),
      );
      await settle();
      assert.equal(
        (await api.request(`${config.endpoint}/get?id=${id}`)).body.data.status,
        0,
      );
      await control.click();
      await ui.responseDuring(`${config.endpoint}/update-status`, 'PUT', () =>
        ui.confirm(),
      );
      await settle();
      assert.equal(
        (await api.request(`${config.endpoint}/get?id=${id}`)).body.data.status,
        1,
      );
    });
    await test(`${config.label}：搜索空结果与重置`, async () => {
      await goto(config.path);
      await ui.search(config.nameLabel, '不存在的QA记录');
      await settle();
      await page
        .locator('#__vben_main_content')
        .getByText('暂无数据', { exact: true })
        .filter({ visible: true })
        .first()
        .waitFor();
      await ui
        .main()
        .getByRole('button', { name: '重置', exact: true })
        .click();
      await ui.rows(id).first().waitFor();
    });
  }
  await test('部门：清空邮箱后的保存对照', async () => {
    await goto('/system/dept');
    await ui.search('部门名称', state.dept.name);
    await settle();
    await ui.rowButton(state.dept.id, '修改');
    await page.waitForTimeout(250);
    await ui.fill('邮箱', 'qa@example.test');
    await ui.fill('邮箱', '');
    await ui.fill('部门名称', `${state.dept.name}改`);
    await ui.responseDuring('/admin-api/system/dept/update', 'PUT', () =>
      ui.dialog().getByRole('button', { name: '确认', exact: true }).click(),
    );
    await ui.dialog().waitFor({ state: 'hidden' });
    state.dept.name += '改';
    await writeFile(
      join(work, 'core-state.json'),
      JSON.stringify(state, null, 2),
    );
    return {
      diagnostic: '此步骤显式清空了邮箱，仅用于定位，不代表原样编辑通过',
    };
  });
}
