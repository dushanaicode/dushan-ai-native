import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function runProfileProbes(api) {
  const { page, goto, test, assert, settle, work, output } = api;
  const ui = controls(page, assert);
  await test('个人中心：基本资料保存与还原', async () => {
    await goto('/profile');
    const field = ui.main().getByRole('textbox', { name: '地址', exact: true });
    const old = await field.inputValue();
    await field.fill('QA 浏览器测试地址');
    await ui
      .main()
      .getByRole('tabpanel', { name: '基本信息', exact: true })
      .getByRole('button', { name: '保存', exact: true })
      .click();
    await settle();
    await page.reload();
    await settle();
    assert.equal(await field.inputValue(), 'QA 浏览器测试地址');
    await field.fill(old);
    await ui
      .main()
      .getByRole('tabpanel', { name: '基本信息', exact: true })
      .getByRole('button', { name: '保存', exact: true })
      .click();
    await settle();
  });
  await test('个人中心：AI 偏好保存与在线设备信息', async () => {
    await goto('/profile');
    await ui.main().getByRole('tab', { name: 'AI 偏好', exact: true }).click();
    const field = ui
      .main()
      .getByRole('textbox', { name: '专业领域', exact: true });
    const old = await field.inputValue();
    await field.fill('浏览器自动化测试');
    await ui
      .main()
      .getByRole('tabpanel', { name: 'AI 偏好', exact: true })
      .getByRole('button', { name: '保存', exact: true })
      .click();
    await settle();
    await field.fill(old);
    await ui
      .main()
      .getByRole('tabpanel', { name: 'AI 偏好', exact: true })
      .getByRole('button', { name: '保存', exact: true })
      .click();
    await settle();
    await ui.main().getByRole('tab', { name: '在线设备', exact: true }).click();
    await settle();
    await writeFile(
      join(output, 'online-devices.txt'),
      await ui.main().ariaSnapshot(),
    );
    const body = await ui.main().innerText();
    assert(body.includes('127.0.0.1'));
    assert(/Chrome|Windows/.test(body));
  });
  await test('用户导入：前端文件丢失后的独立浏览器 API 验证', async () => {
    await goto('/system/user');
    const result = await api.upload(
      '/admin-api/system/user/import',
      join(work, 'user-import.xlsx'),
      { updateSupport: false },
    );
    await writeFile(
      join(output, 'import-result.json'),
      JSON.stringify(result, null, 2),
    );
    assert.equal(result.body.code, 0);
    assert(result.body.data.createUsernames.includes('qaimport'));
  });
  await test('用户导入：重复数据与允许更新 API 边界', async () => {
    const duplicate = await api.upload(
      '/admin-api/system/user/import',
      join(work, 'user-import.xlsx'),
      { updateSupport: false },
    );
    assert.equal(duplicate.body.code, 0);
    assert(duplicate.body.data.failureUsernames.qaimport);
    const update = await api.upload(
      '/admin-api/system/user/import',
      join(work, 'user-import-update.xlsx'),
      { updateSupport: true },
    );
    assert.equal(update.body.code, 0);
    assert(update.body.data.updateUsernames.includes('qaimport'));
    await writeFile(
      join(output, 'import-boundaries.json'),
      JSON.stringify({ duplicate, update }, null, 2),
    );
  });
  const core = JSON.parse(
    await readFile(join(work, 'core-state.json'), 'utf8'),
  );
  const account = JSON.parse(
    await readFile(join(work, 'accounts-state.json'), 'utf8'),
  );
  const infra = JSON.parse(
    await readFile(join(work, 'infra-state.json'), 'utf8'),
  );
  for (const path of [
    '/system/auth/codes',
    '/system/auth/registration-enabled',
    '/system/dict/type/simple-list',
    '/system/mail/template/simple-list',
    '/system/tenant/simple-list',
    '/system/area/get-by-ip?ip=127.0.0.1',
    `/system/tenant/get-id-by-name?name=${encodeURIComponent('渡山无界')}`,
    `/system/tenant/get-by-website?website=${encodeURIComponent('http://localhost')}`,
    `/system/permission/list-role-menus-by-ids?roleIds=${core.role.id}`,
    `/system/sms/channel/callback-url?id=${account.smsChannel.id}`,
    '/infra/data-source/list-by-status?status=1',
    '/infra/file/page?page=1&pageSize=20',
    `/infra/file/config/test?id=${infra.fileConfig.id}`,
    '/system/notification/message/get-unread-count',
    '/system/notification/message/get-unread-list',
  ]) {
    await test(`补充只读接口 ${path.split('?')[0]}`, async () => {
      const result = await api.request(`/admin-api${path}`);
      assert.equal(result.body.code, 0);
      return {
        source: 'browser-api',
        dataType: typeof result.body.data,
        count: Array.isArray(result.body.data)
          ? result.body.data.length
          : undefined,
      };
    });
  }
}
