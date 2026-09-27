import { writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function runCoreCrud(api) {
  const { page, goto, test, assert, settle, work } = api;
  const ui = controls(page, assert);
  const state = {};
  const suffix = Date.now().toString(36).slice(-6);
  const configs = [
    {
      key: 'post',
      label: '岗位',
      path: '/system/post',
      endpoint: '/admin-api/system/dept/post',
      nameLabel: '岗位名称',
      codeLabel: '岗位编码',
      sortLabel: '显示顺序',
      remarkLabel: '备注',
    },
    {
      key: 'role',
      label: '角色',
      path: '/system/role',
      endpoint: '/admin-api/system/permission/role',
      nameLabel: '角色名称',
      codeLabel: '角色标识',
      sortLabel: '显示顺序',
      remarkLabel: '角色备注',
    },
    {
      key: 'dept',
      label: '部门',
      path: '/system/dept',
      endpoint: '/admin-api/system/dept',
      nameLabel: '部门名称',
      sortLabel: '显示顺序',
      parent: ['上级部门', '顶级部门'],
    },
  ];
  for (const config of configs) {
    let id;
    const name = `QA${config.label}${suffix}`;
    await test(`${config.label}：新增与真实回读`, async () => {
      await goto(config.path);
      id = await ui.create(`新增${config.label}`, config.endpoint, async () => {
        if (config.parent) await ui.select(...config.parent);
        await ui.fill(config.nameLabel, name);
        if (config.codeLabel)
          await ui.fill(config.codeLabel, `qa_${config.key}_${suffix}`);
        await ui.fill(config.sortLabel, 0);
        if (config.remarkLabel)
          await ui.fill(config.remarkLabel, '浏览器完整流程');
      });
      await settle();
      const detail = await api.request(`${config.endpoint}/get?id=${id}`);
      assert.equal(detail.body.code, 0);
      assert.equal(detail.body.data.name, name);
      state[config.key] = { id, name, code: `qa_${config.key}_${suffix}` };
      return state[config.key];
    });
    if (!id) continue;
    await test(`${config.label}：编辑回填与保存`, async () => {
      await ui.search(config.nameLabel, name);
      await settle();
      await ui.rowButton(id, '修改');
      await page.waitForTimeout(200);
      assert.equal(
        await ui
          .dialog()
          .getByLabel(new RegExp(`${config.nameLabel}$`))
          .inputValue(),
        name,
      );
      await ui.fill(config.nameLabel, `${name}改`);
      await ui.responseDuring(`${config.endpoint}/update`, 'PUT', () =>
        ui.dialog().getByRole('button', { name: '确认', exact: true }).click(),
      );
      await ui.dialog().waitFor({ state: 'hidden' });
      await settle();
      const detail = await api.request(`${config.endpoint}/get?id=${id}`);
      assert.equal(detail.body.data.name, `${name}改`);
      state[config.key].name = `${name}改`;
    });
    await test(`${config.label}：停用与恢复`, async () => {
      await goto(config.path);
      await ui.search(config.nameLabel, name);
      await settle();
      for (const expected of [0, 1]) {
        await ui.rows(id).getByRole('switch').last().click();
        await ui.responseDuring(`${config.endpoint}/update-status`, 'PUT', () =>
          ui.confirm(),
        );
        await settle();
        const detail = await api.request(`${config.endpoint}/get?id=${id}`);
        assert.equal(detail.body.data.status, expected);
      }
    });
    await test(`${config.label}：搜索与重置`, async () => {
      await goto(config.path);
      await ui.search(config.nameLabel, `不存在_${suffix}`);
      await settle();
      assert.equal(
        await page.getByRole('main').locator('tr[rowid]').count(),
        0,
      );
      await page
        .getByRole('main')
        .getByRole('button', { name: '重置', exact: true })
        .click();
      await settle();
      assert((await ui.rows(id).count()) > 0);
    });
  }
  await writeFile(
    join(work, 'core-state.json'),
    JSON.stringify(state, null, 2),
  );
}
