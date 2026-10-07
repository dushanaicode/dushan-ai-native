import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function runMessagesImport(api) {
  const { page, goto, test, assert, settle, work, output } = api;
  const ui = controls(page, assert);
  const state = JSON.parse(
    await readFile(join(work, 'content-state.json'), 'utf8'),
  );
  for (const [name, file, update, expected] of [
    ['导入新用户', 'user-import.xlsx', false, '新增 1 个'],
    ['重复导入不覆盖', 'user-import.xlsx', false, '失败 1 个'],
    ['导入并更新既有用户', 'user-import-update.xlsx', true, '更新 1 个'],
  ]) {
    await test(`用户：${name}`, async () => {
      await goto('/system/user');
      await ui
        .main()
        .getByRole('button', { name: '导入', exact: true })
        .click();
      await ui
        .dialog()
        .locator('input[type="file"]')
        .setInputFiles(join(work, file));
      if (update) await ui.dialog().locator('.el-switch').click();
      await ui.responseDuring('/admin-api/system/user/import', 'POST', () =>
        ui.dialog().getByRole('button', { name: '确认', exact: true }).click(),
      );
      await settle();
      await writeFile(
        join(output, `${file}.txt`),
        await ui.dialog().ariaSnapshot(),
      );
      assert((await ui.dialog().innerText()).includes(expected));
      await ui
        .dialog()
        .getByRole('button', { name: '确认', exact: true })
        .click();
    });
  }
  await test('通知：选择用户、弹窗位置、推送给当前测试管理员', async () => {
    await goto('/system/notification/notice');
    await ui.rowButton(state.notice.id, '更多');
    await page
      .getByRole('menuitem')
      .filter({ hasText: /推送/ })
      .first()
      .click();
    await settle();
    await ui
      .dialog()
      .getByRole('button', { name: '请选择目标用户', exact: true })
      .click();
    await settle();
    const picker = ui.dialog();
    await page.waitForTimeout(400);
    const box = await picker.boundingBox();
    const viewport = page.viewportSize();
    await writeFile(
      join(output, 'picker-geometry.json'),
      JSON.stringify({ box, viewport }),
    );
    assert(
      box.y >= 0 && box.y + box.height <= viewport.height + 2,
      '选择用户弹窗超出视口',
    );
    await picker.getByPlaceholder('输入账号或名称').fill('admin');
    await picker.getByRole('button', { name: '搜索', exact: true }).click();
    await settle();
    await writeFile(
      join(output, 'user-picker.txt'),
      await picker.ariaSnapshot(),
    );
    await picker
      .getByRole('row')
      .filter({ hasText: '管理员' })
      .locator('.el-checkbox')
      .first()
      .click();
    await picker.getByRole('button', { name: '确定', exact: true }).click();
    await ui.responseDuring(
      '/admin-api/system/notification/push-targets',
      'POST',
      () =>
        ui.dialog().getByRole('button', { name: '确认', exact: true }).click(),
    );
    await ui.dialog().waitFor({ state: 'hidden' });
  });
  await test('站内信：收到通知、详情和标记已读', async () => {
    await goto('/my-notice-message');
    const title = state.notice.record.title;
    const row = ui.main().locator('tr[rowid]').filter({ hasText: title });
    await row
      .getByRole('button', { name: '已读并查看', exact: true })
      .last()
      .click();
    await ui.dialog().waitFor();
    await settle();
    assert((await ui.dialog().innerText()).includes('浏览器站内信测试内容'));
    await ui.close();
    await ui
      .main()
      .getByRole('button', { name: '全部已读', exact: true })
      .click();
    await ui.confirm();
    await settle();
    assert.equal(
      (
        await api.request(
          '/admin-api/system/notification/message/get-unread-count',
        )
      ).body.data,
      0,
    );
  });
}
