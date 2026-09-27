import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { controls } from './ui.mjs';

export default async function runDeliveryRound2(api) {
  const { page, goto, test, assert, settle, work, output } = api;
  const ui = controls(page, assert);
  const state = JSON.parse(
    await readFile(join(work, 'content-state.json'), 'utf8'),
  );
  const accounts = JSON.parse(
    await readFile(join(work, 'accounts-state.json'), 'utf8'),
  );
  let logId;
  await test('短信：浏览器测试发送、模板参数和本地适配器接收', async () => {
    await goto('/system/message/sms/template');
    await ui.rowButton(state.smsTemplate.id, '测试发送');
    await settle();
    await ui.fill('手机号码', '13900139009');
    await ui.fill('code', '975310');
    logId = await ui.responseDuring(
      '/admin-api/system/sms/template/send-sms',
      'POST',
      () =>
        ui.dialog().getByRole('button', { name: '确认', exact: true }).click(),
    );
    await ui.dialog().waitFor({ state: 'hidden' });
    let received;
    for (let attempt = 0; attempt < 40; attempt++) {
      try {
        received = JSON.parse(
          await readFile(join(work, 'sms-inbox.json'), 'utf8'),
        ).find((item) => item.mobile === '13900139009');
      } catch (error) {
        if (error.code !== 'ENOENT') throw error;
      }
      if (received) break;
      await page.waitForTimeout(250);
    }
    assert(received, '本地短信适配器未收到发送');
    assert.equal(received.params.code, '975310');
    await goto('/system/message/sms/log');
    const detail = (
      await api.request('/admin-api/system/sms/log/page?page=1&pageSize=20')
    ).body.data.items.find((item) => item.id === logId);
    assert.equal(detail.sendStatus, 10);
    await writeFile(
      join(output, 'sms-delivery.json'),
      JSON.stringify(
        {
          logId,
          sendStatus: detail.sendStatus,
          adapter: '模拟阿里云发送，未产生外部短信',
        },
        null,
        2,
      ),
    );
  });
  if (logId) {
    await test('短信回执：签名地址与模拟投递回执更新', async () => {
      const callback = await api.request(
        `/admin-api/system/sms/channel/callback-url?id=${accounts.smsChannel.id}`,
      );
      assert.equal(callback.body.code, 0);
      const url = new URL(callback.body.data);
      const response = await api.request(url.pathname + url.search, {
        method: 'POST',
        auth: false,
        credentials: 'omit',
        data: [
          {
            success: true,
            err_code: 'DELIVERED',
            err_msg: 'QA delivered',
            phone_number: '13900139009',
            report_time: '2026-09-25 13:20:00',
            biz_id: 'qa-sms',
            out_id: logId,
          },
        ],
      });
      assert.equal(response.body.code, 0);
      const detail = (
        await api.request('/admin-api/system/sms/log/page?page=1&pageSize=20')
      ).body.data.items.find((item) => item.id === logId);
      assert.equal(detail.receiveStatus, 10);
    });
  }
  await test('任务：健康运行时触发真实清理任务并产生日志', async () => {
    await goto('/infra/job');
    const job = (
      await api.request('/admin-api/infra/job/page?page=1&pageSize=20')
    ).body.data.items.find(
      (item) => item.handlerName === 'infra.job.log.clean',
    );
    await ui.rowButton(job.id, '更多');
    await page.getByRole('menuitem', { name: '执行一次', exact: true }).click();
    await ui.responseDuring('/admin-api/infra/job/trigger', 'PUT', () =>
      page
        .locator('.el-popconfirm:visible')
        .getByRole('button', { name: '确定', exact: true })
        .click(),
    );
    let rows;
    for (let attempt = 0; attempt < 40; attempt++) {
      rows = (
        await api.request(
          `/admin-api/infra/job/log/page?page=1&pageSize=20&jobId=${job.id}`,
        )
      ).body.data.items;
      if (rows.length > 0) break;
      await page.waitForTimeout(250);
    }
    assert(rows.length > 0, '没有生成任务执行记录');
    await writeFile(
      join(output, 'job-execution.json'),
      JSON.stringify(rows, null, 2),
    );
  });
  await test('邮件：发送日志确认实际 SMTP 成功', async () => {
    await goto('/system/message/mail/log');
    const logs = (
      await api.request('/admin-api/system/mail/log/page?page=1&pageSize=20')
    ).body.data.items;
    assert(logs.some((log) => log.sendStatus === 10));
    const detail = await api.request(
      `/admin-api/system/mail/log/get?id=${logs[0].id}`,
    );
    assert.equal(detail.body.code, 0);
  });
}
