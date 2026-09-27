import { writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function runPublicAuthNegative(api) {
  const { page, goto, test, assert, output, settle, server } = api;
  const ui = controls(page, assert);
  await goto('/dashboard/analytics');
  const cases = [
    [
      '未绑定手机号发送登录码',
      '/system/auth/send-sms-code',
      'POST',
      { mobile: '13900139099', scene: 21 },
    ],
    [
      '错误短信码不能登录',
      '/system/auth/sms-login',
      'POST',
      { mobile: '13900139099', code: '000000' },
    ],
    [
      '错误重置码不能更改密码',
      '/system/auth/reset-password',
      'POST',
      {
        channel: 'sms',
        mobile: '13900139099',
        code: '000000',
        password: 'QAInvalidReset123',
      },
    ],
    [
      '无效社交状态不能登录',
      '/system/auth/social-login',
      'POST',
      { type: 20, code: 'qa-invalid', state: 'qa-invalid' },
    ],
    ['禁用验证码获取', '/system/captcha/get', 'POST', { purpose: 'login' }],
    [
      '无效验证码校验',
      '/system/captcha/check',
      'POST',
      { purpose: 'login', challengeId: 'qa-invalid', answer: {} },
    ],
    [
      '未配置社交渠道跳转',
      `/system/auth/social-auth-redirect?type=20&redirectUri=${encodeURIComponent(
        `${server.origin}/auth/social-login`,
      )}`,
      'GET',
    ],
    [
      '无效 GET 社交回调',
      '/system/auth/social-callback?state=qa-invalid&code=qa-invalid',
      'GET',
    ],
    [
      '无效 POST 社交回调',
      '/system/auth/social-callback',
      'POST',
      undefined,
      { state: 'qa-invalid', code: 'qa-invalid' },
    ],
    ['无效短信签名回调', '/system/sms/callback?token=qa-invalid', 'POST', []],
  ];
  const observations = [];
  for (const [name, path, method, data, form] of cases) {
    const allowedCodes = [];
    await test(
      `公开接口拒绝分支：${name}`,
      async () => {
        const response = await api.request(`/admin-api${path}`, {
          method,
          data,
          form,
          auth: false,
          credentials: 'omit',
          headers: { 'X-Tenant-Id': '1' },
        });
        allowedCodes.push(response.body.code);
        observations.push({
          name,
          path: path.split('?')[0],
          code: response.body.code,
          message: response.body.message,
        });
        assert.notEqual(response.body.code, 0, '不应接受无效凭据或未配置能力');
        assert.notEqual(
          response.body.code,
          500,
          '输入/配置条件不应成为系统异常',
        );
        return observations.at(-1);
      },
      { allowedCodes },
    );
  }
  const recoveryCodes = [];
  await test(
    '找回密码：未绑定目标不泄露账号存在性',
    async () => {
      const response = await api.request(
        '/admin-api/system/auth/send-password-reset-code',
        {
          method: 'POST',
          auth: false,
          credentials: 'omit',
          headers: { 'X-Tenant-Id': '1' },
          data: { channel: 'sms', mobile: '13900139099' },
        },
      );
      recoveryCodes.push(response.body.code);
      observations.push({
        name: '找回未绑定目标',
        code: response.body.code,
        message: response.body.message,
      });
      assert.equal(response.body.code, 0);
      assert([4, 5, 6].includes(response.body.data));
    },
    { allowedCodes: recoveryCodes },
  );
  await writeFile(
    join(output, 'public-boundaries.json'),
    JSON.stringify(observations, null, 2),
  );
  await test('退出登录：通过页头操作退出并回到登录页', async () => {
    await goto('/dashboard/analytics');
    const buttons = page.getByRole('banner').getByRole('button');
    const logout = buttons.nth((await buttons.count()) - 2);
    await logout.hover();
    await page.waitForTimeout(400);
    await writeFile(
      join(output, 'header-controls.txt'),
      await page.getByRole('banner').ariaSnapshot(),
    );
    await logout.click();
    await ui.responseDuring(
      '/admin-api/system/auth/logout',
      'POST',
      ui.confirm,
    );
    await page.getByPlaceholder('请输入用户名').waitFor();
    await settle();
  });
}
