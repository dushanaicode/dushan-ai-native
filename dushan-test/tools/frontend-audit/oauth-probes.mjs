import { Buffer } from 'node:buffer';
import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

export default async function runOauthProbes(api) {
  const { test, assert, work, server } = api;
  await api.goto('/system/oauth2/client');
  const account = JSON.parse(
    await readFile(join(work, 'accounts-state.json'), 'utf8'),
  ).user;
  const clientId = 'qa_browser_api';
  const secret = 'QAtest-Client-Secret-1234567890-AbCd!';
  const basic = {
    Authorization: `Basic ${Buffer.from(`${clientId}:${secret}`).toString('base64')}`,
  };
  let tokens;
  await test('OAuth API：创建隔离客户端作为开放接口测试准备', async () => {
    const response = await api.request(
      '/admin-api/system/oauth2/client/create',
      {
        method: 'POST',
        data: {
          clientId,
          secret,
          name: 'QA开放接口客户端',
          logo: `${server.origin}/favicon.ico`,
          status: 1,
          userType: 2,
          accessTokenValiditySeconds: 1800,
          refreshTokenValiditySeconds: 3600,
          redirectUris: [`${server.origin}/qa-callback`],
          authorizedGrantTypes: [
            'password',
            'refresh_token',
            'authorization_code',
          ],
          scopes: ['user.read', 'user.write'],
          autoApproveScopes: [],
          authorities: [],
          resourceIds: [],
        },
      },
    );
    assert.equal(response.body.code, 0);
    await writeFile(
      join(work, 'oauth-probe-client.json'),
      JSON.stringify({ id: response.body.data, clientId }),
    );
  });
  await test('OAuth API：密码授权及用户身份读取', async () => {
    const response = await api.request('/admin-api/system/oauth2/open/token', {
      method: 'POST',
      auth: false,
      headers: basic,
      form: {
        grant_type: 'password',
        username: account.record.username,
        password: 'Qatest123',
        scope: 'user.read user.write',
      },
    });
    assert.equal(response.body.code, 0);
    tokens = response.body.data;
    assert(tokens.accessToken && tokens.refreshToken);
    const user = await api.request('/admin-api/system/oauth2/user/get', {
      auth: false,
      headers: { Authorization: `Bearer ${tokens.accessToken}` },
    });
    assert.equal(user.body.code, 0);
    assert.equal(user.body.data.username, account.record.username);
  });
  if (tokens) {
    await test('OAuth API：授权范围内更新用户与令牌校验', async () => {
      const changed = await api.request(
        '/admin-api/system/oauth2/user/update',
        {
          method: 'PUT',
          auth: false,
          headers: { Authorization: `Bearer ${tokens.accessToken}` },
          data: {
            nickname: account.record.nickname,
            email: account.record.email,
            mobile: account.record.mobile,
            sex: account.record.sex,
          },
        },
      );
      assert.equal(changed.body.code, 0);
      const checked = await api.request(
        `/admin-api/system/oauth2/open/check-token?token=${encodeURIComponent(tokens.accessToken)}`,
        { method: 'POST', auth: false, headers: basic },
      );
      assert.equal(checked.body.code, 0);
    });
    await test('OAuth API：刷新令牌轮换和撤销', async () => {
      const refreshed = await api.request(
        '/admin-api/system/oauth2/open/token',
        {
          method: 'POST',
          auth: false,
          headers: basic,
          form: {
            grant_type: 'refresh_token',
            refresh_token: tokens.refreshToken,
          },
        },
      );
      assert.equal(refreshed.body.code, 0);
      assert.notEqual(refreshed.body.data.accessToken, tokens.accessToken);
      tokens = refreshed.body.data;
      const revoked = await api.request(
        `/admin-api/system/oauth2/open/token?token=${encodeURIComponent(tokens.accessToken)}`,
        { method: 'DELETE', auth: false, headers: basic },
      );
      assert.equal(revoked.body.code, 0);
      assert.equal(revoked.body.data, true);
    });
  }
  await test('OAuth API：授权页面数据、授权码交换', async () => {
    const info = await api.request(
      `/admin-api/system/oauth2/open/authorize?client_id=${clientId}`,
    );
    assert.equal(info.body.code, 0);
    const query = new URLSearchParams({
      client_id: clientId,
      redirect_uri: `${server.origin}/qa-callback`,
      auto_approve: 'false',
      response_type: 'code',
      scope: JSON.stringify({ 'user.read': true }),
      state: 'qa-state',
    });
    const authorized = await api.request(
      `/admin-api/system/oauth2/open/authorize?${query}`,
      {
        method: 'POST',
      },
    );
    assert.equal(authorized.body.code, 0);
    const code = new URL(authorized.body.data).searchParams.get('code');
    assert(code);
    const exchange = await api.request('/admin-api/system/oauth2/open/token', {
      method: 'POST',
      auth: false,
      headers: basic,
      form: {
        grant_type: 'authorization_code',
        code,
        redirect_uri: `${server.origin}/qa-callback`,
        state: 'qa-state',
      },
    });
    assert.equal(exchange.body.code, 0);
    assert(exchange.body.data.accessToken);
  });
  const allowedCodes = [];
  await test(
    '注册关闭：服务端拒绝直接调用注册',
    async () => {
      const response = await api.request('/admin-api/system/auth/register', {
        method: 'POST',
        auth: false,
        headers: { 'X-Tenant-Id': '1' },
        data: {
          username: 'qaregisterdenied',
          nickname: 'QA禁止注册',
          password: 'QAtest123',
        },
      });
      allowedCodes.push(response.body.code);
      assert.notEqual(response.body.code, 0);
      assert(/注册|regist/i.test(response.body.message));
      const users = await api.request(
        '/admin-api/system/user/page?username=qaregisterdenied',
      );
      assert.equal(users.body.data.total, 0);
      return {
        rejectedCode: response.body.code,
        message: response.body.message,
      };
    },
    { allowedCodes },
  );
  await test('第三方登录关闭：公开渠道为空', async () => {
    const response = await api.request(
      '/admin-api/system/auth/social-providers',
      {
        auth: false,
        headers: { 'X-Tenant-Id': '1' },
      },
    );
    assert.equal(response.body.code, 0);
    assert.equal(response.body.data.length, 0);
  });
}
