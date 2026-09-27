import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function runFinalContracts(api) {
  const { page, goto, test, assert, settle, work, output, server } = api;
  const ui = controls(page, assert);
  await test('OAuth 客户端：修改名称且不改密钥的接口契约', async () => {
    await goto('/system/oauth2/client');
    const data = {
      clientId: 'qa_edit_contract',
      name: 'QA密钥编辑契约',
      logo: `${server.origin}/favicon.ico`,
      status: 1,
      userType: 2,
      accessTokenValiditySeconds: 1800,
      refreshTokenValiditySeconds: 3600,
      redirectUris: [server.origin],
      authorizedGrantTypes: ['password'],
      scopes: ['user.read'],
      autoApproveScopes: [],
      authorities: [],
      resourceIds: [],
    };
    const created = await api.request(
      '/admin-api/system/oauth2/client/create',
      {
        method: 'POST',
        data: { ...data, secret: 'QAtest-Secret-1234567890-abcdefgh!' },
      },
    );
    assert.equal(created.body.code, 0);
    const response = await api.request(
      '/admin-api/system/oauth2/client/update',
      {
        method: 'PUT',
        data: { ...data, id: created.body.data, name: 'QA只改名称' },
      },
    );
    await writeFile(
      join(output, 'oauth-update-contract.json'),
      JSON.stringify(
        {
          code: response.body.code,
          message: response.body.message,
          error: response.body.error,
        },
        null,
        2,
      ),
    );
    assert.equal(response.body.code, 0, '省略密钥应当保留原密钥');
  });
  const negativeCodes = [];
  await test(
    '验证码错误：真实账号错误短信码拒绝登录和重置',
    async () => {
      await goto('/system/user');
      const user = await api.request('/admin-api/system/user/create', {
        method: 'POST',
        data: {
          username: 'qarecovery',
          nickname: 'QA验证码用户',
          password: 'QAtest123',
          mobile: '13900139099',
        },
      });
      assert.equal(user.body.code, 0);
      const headers = { 'X-Tenant-Id': '1' };
      const login = await api.request('/admin-api/system/auth/sms-login', {
        method: 'POST',
        auth: false,
        credentials: 'omit',
        headers,
        data: { mobile: '13900139099', code: '000000' },
      });
      const reset = await api.request('/admin-api/system/auth/reset-password', {
        method: 'POST',
        auth: false,
        credentials: 'omit',
        headers,
        data: {
          channel: 'sms',
          mobile: '13900139099',
          code: '000000',
          password: 'QAReset123!',
        },
      });
      negativeCodes.push(login.body.code, reset.body.code);
      assert.equal(login.body.code, 1_002_014_000);
      assert.equal(reset.body.code, 1_002_014_000);
      const stillValid = await api.request('/admin-api/system/auth/login', {
        method: 'POST',
        auth: false,
        credentials: 'omit',
        headers,
        data: { username: 'qarecovery', password: 'QAtest123' },
      });
      assert.equal(stillValid.body.code, 0);
    },
    { allowedCodes: negativeCodes },
  );
  const state = JSON.parse(
    await readFile(join(work, 'content-state.json'), 'utf8'),
  );
  await test('短信模板：停用、启用与删除', async () => {
    await goto('/system/message/sms/template');
    for (const status of [0, 1]) {
      await ui.rows(state.smsTemplate.id).locator('.el-switch').last().click();
      await ui.responseDuring(
        '/admin-api/system/sms/template/update-status',
        'PUT',
        ui.confirm,
      );
      await page.getByRole('alertdialog').waitFor({ state: 'hidden' });
      await settle();
      assert.equal(
        (
          await api.request(
            `/admin-api/system/sms/template/get?id=${state.smsTemplate.id}`,
          )
        ).body.data.status,
        status,
      );
    }
    await ui.rowButton(state.smsTemplate.id, '删除');
    await ui.responseDuring(
      '/admin-api/system/sms/template/delete',
      'DELETE',
      () =>
        page
          .locator('.el-popconfirm:visible')
          .getByRole('button', { name: '确定', exact: true })
          .click(),
    );
  });
}
