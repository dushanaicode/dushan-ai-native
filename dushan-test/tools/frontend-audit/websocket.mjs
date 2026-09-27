import { writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function runWebsocket(api) {
  const { page, goto, test, assert, settle, output } = api;
  const ui = controls(page, assert);
  let refreshCount = 0;
  page.on('response', (response) => {
    if (new URL(response.url()).pathname.endsWith('/auth/refresh-token'))
      refreshCount++;
  });
  page.setDefaultTimeout(30_000);
  await api.login();
  await goto('/infra/webSocket');
  await page.waitForTimeout(1500);
  await page.reload();
  await settle();
  const received = () =>
    ui
      .main()
      .locator('.el-card')
      .filter({ has: page.getByText('接收日志', { exact: true }) });
  await test('WebSocket：真实连接与手动心跳', async () => {
    await ui.main().getByText('已连接', { exact: true }).waitFor();
    await ui
      .main()
      .getByRole('button', { name: '发送直连消息', exact: true })
      .click();
    await received().getByText(/pong/).first().waitFor();
  });
  await test('WebSocket：HTTP 广播送达到接收面板', async () => {
    await goto('/infra/webSocket');
    await ui.main().getByText('已连接', { exact: true }).waitFor();
    const message = JSON.stringify({
      type: 'broadcast',
      payload: { title: 'QA广播', content: 'QA-broadcast-delivered' },
    });
    await ui.main().locator('textarea').nth(1).fill(message);
    await ui
      .main()
      .getByRole('button', { name: '广播到当前租户的调试连接', exact: true })
      .click();
    await received()
      .getByText(/QA-broadcast-delivered/)
      .waitFor();
  });
  await test('WebSocket：HTTP 定向消息送达到当前用户', async () => {
    await ui.main().getByRole('combobox').last().press('Enter');
    await page.getByRole('option', { name: '管理员', exact: true }).click();
    await ui
      .main()
      .locator('textarea')
      .nth(2)
      .fill(
        JSON.stringify({
          type: 'notice_message',
          payload: { content: 'QA-target-delivered' },
        }),
      );
    await ui
      .main()
      .getByRole('button', { name: '发送给用户', exact: true })
      .click();
    await received()
      .getByText(/QA-target-delivered/)
      .waitFor();
  });
  await test('WebSocket：令牌真实过期、静默续期后继续收消息', async () => {
    const client = (
      await api.request('/admin-api/system/oauth2/client/get?id=10100000080001')
    ).body.data;
    assert.equal(client.accessTokenValiditySeconds, 20, '短令牌测试前提未生效');
    const before = refreshCount;
    await page.waitForTimeout(25_000);
    await ui.main().getByText('已连接', { exact: true }).waitFor();
    await ui
      .main()
      .locator('textarea')
      .nth(1)
      .fill(
        JSON.stringify({
          type: 'broadcast',
          payload: { content: 'QA-after-expiry' },
        }),
      );
    await ui
      .main()
      .getByRole('button', { name: '广播到当前租户的调试连接', exact: true })
      .click();
    await received()
      .getByText(/QA-after-expiry/)
      .waitFor();
    assert(refreshCount > before, '没有发生实际令牌续期，不能视为过期测试通过');
    assert.equal(
      await page
        .locator('.el-message')
        .filter({ hasText: /过期|失效/ })
        .count(),
      0,
    );
    await writeFile(
      join(output, 'after-expiry.txt'),
      await ui.main().ariaSnapshot(),
    );
  });
  await test('WebSocket：手动断开和重连', async () => {
    await ui.main().getByRole('button', { name: '断开', exact: true }).click();
    await ui.main().getByRole('button', { name: '连接', exact: true }).click();
    await ui.main().getByText('已连接', { exact: true }).waitFor();
    await ui
      .main()
      .getByRole('button', { name: '发送直连消息', exact: true })
      .click();
    await received().getByText(/pong/).first().waitFor();
  });
}
