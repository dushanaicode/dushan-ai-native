import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

export default async function runAuthRoles(api) {
  const { context, goto, test, assert, work, output, server } = api;
  const core = JSON.parse(
    await readFile(join(work, 'core-state.json'), 'utf8'),
  );
  const accounts = JSON.parse(
    await readFile(join(work, 'accounts-state.json'), 'utf8'),
  );
  const admin = JSON.parse(
    await readFile(join(work, 'admin-state.json'), 'utf8'),
  );
  await goto('/system/user');
  const menuList = (await api.request('/admin-api/system/permission/menu/list'))
    .body.data;
  const byId = new Map(menuList.map((menu) => [menu.id, menu]));
  const query = menuList.find(
    (menu) => menu.permission === 'system:user:query',
  );
  const permitted = [];
  for (let menu = query; menu; menu = byId.get(menu.parentId))
    permitted.push(menu.id);
  const assign = (ids) =>
    api.request('/admin-api/system/permission/assign-role-menu', {
      method: 'POST',
      data: { roleId: core.role.id, menuIds: ids },
    });
  const actorContext = await context
    .browser()
    .newContext({ viewport: { width: 1600, height: 1000 } });
  const actor = await actorContext.newPage();
  actor.setDefaultTimeout(10_000);
  const actorCalls = [];
  const pending = new Set();
  let token;
  let current;
  actor.on('request', (request) => {
    if (request.headers().authorization)
      token = request.headers().authorization;
  });
  actor.on('response', (response) => {
    if (!response.url().includes('/admin-api/')) return;
    const value = {
      case: current,
      method: response.request().method(),
      url: new URL(response.url()).pathname,
      http: response.status(),
    };
    actorCalls.push(value);
    const task = response.json().then((body) => {
      value.code = body.code;
      value.message = body.message;
      if (value.url.endsWith('/auth/login') && body.code === 0)
        token = `Bearer ${body.data.accessToken}`;
    });
    pending.add(task);
    task.finally(() => pending.delete(task));
  });
  async function login(username, password, tenant) {
    await actor.goto(`${server.origin}/#/auth/login`);
    await actor.getByPlaceholder('请输入用户名').fill(username);
    await actor.getByRole('combobox').first().press('Enter');
    await actor.getByRole('option', { name: tenant, exact: true }).click();
    await actor.getByPlaceholder('密码', { exact: true }).fill(password);
    const [response] = await Promise.all([
      actor.waitForResponse((response) =>
        response.url().endsWith('/auth/login'),
      ),
      actor.getByRole('button', { name: 'login', exact: true }).click(),
    ]);
    assert.equal((await response.json()).code, 0);
    await actor.waitForURL((url) => !url.hash.startsWith('#/auth/'));
    await actor.locator('#__vben_main_content').waitFor();
  }
  async function actorFetch(path) {
    return actor.evaluate(
      async ({ path, token }) =>
        (await fetch(path, { headers: { Authorization: token } })).json(),
      { path: `/admin-api${path}`, token },
    );
  }
  async function evidence(name) {
    await actor.screenshot({ path: join(output, `${name}.png`) });
    await writeFile(
      join(output, `${name}.txt`),
      await actor.locator('body').ariaSnapshot(),
    );
  }
  try {
    assert.equal((await assign(permitted)).body.code, 0);
    current = '只读角色与本人数据';
    await test('权限：只读角色隐藏写按钮、本人数据隔离', async () => {
      await login(accounts.user.record.username, 'Qatest123', '渡山无界');
      const [response] = await Promise.all([
        actor.waitForResponse(
          (response) =>
            new URL(response.url()).pathname === '/admin-api/system/user/page',
        ),
        actor.goto(`${server.origin}/#/system/user`),
      ]);
      const body = await response.json();
      assert.equal(body.code, 0);
      assert(body.data.items.length > 0);
      assert(body.data.items.every((item) => item.id === accounts.user.id));
      assert.equal(
        await actor
          .getByRole('button', { name: '新增用户', exact: true })
          .count(),
        0,
      );
      const foreign = await actorFetch('/system/user/get?id=10100000010001');
      assert(!foreign.data, '只读本人角色读取了其他用户');
      await evidence('readonly-role');
    });
    current = '用户修改密码';
    const passwordResult =
      await test('个人密码：修改后用新密码登录', async () => {
        await actor.goto(`${server.origin}/#/profile`);
        await actor.getByRole('tab', { name: '修改密码', exact: true }).click();
        await actor.getByPlaceholder('请输入旧密码').fill('Qatest123');
        await actor
          .getByPlaceholder('请输入新密码', { exact: true })
          .fill('Qatest456!');
        await actor.getByPlaceholder('请再次输入新密码').fill('Qatest456!');
        const [response] = await Promise.all([
          actor.waitForResponse((response) =>
            response.url().endsWith('/profile/update-password'),
          ),
          actor.getByRole('button', { name: '提交', exact: true }).click(),
        ]);
        assert.equal((await response.json()).code, 0);
        assert.equal(
          await actor.evaluate(() =>
            Object.values(localStorage).some((item) =>
              item.includes('Qatest456!'),
            ),
          ),
          false,
        );
        await evidence('password-updated');
      });
    if (passwordResult.status === 'failed') await evidence('password-blocked');
    await actorContext.clearCookies();
    await actor.goto(server.origin);
    await actor.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    current = '新密码登录';
    await test('认证：新密码登录有效', async () => {
      await login(accounts.user.record.username, 'Qatest456!', '渡山无界');
      await evidence('new-password-login');
    });
    await actorContext.clearCookies();
    await actor.goto(server.origin);
    await actor.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    current = '租户隔离';
    await test('租户：新租户登录、列表及跨租户读取隔离', async () => {
      await login('qatenant', 'Qatest123', admin.tenant.record.name);
      const own = await actorFetch('/system/user/page?page=1&pageSize=20');
      assert.equal(own.code, 0);
      assert(own.data.items.length > 0);
      assert(own.data.items.every((item) => item.username === 'qatenant'));
      const foreign = await actorFetch('/system/user/get?id=10100000010001');
      assert(!foreign.data, '新租户读到默认租户用户');
      await actor.goto(`${server.origin}/#/system/user`);
      await actor.waitForTimeout(600);
      await evidence('tenant-isolation');
    });
  } finally {
    await assign(menuList.map((menu) => menu.id));
    await api.request('/admin-api/system/user/update-password', {
      method: 'PUT',
      data: { id: accounts.user.id, password: 'Qatest123' },
    });
    await Promise.all(pending);
    await writeFile(
      join(output, 'actor-calls.json'),
      JSON.stringify(actorCalls, null, 2),
    );
    await actorContext.close();
  }
}
