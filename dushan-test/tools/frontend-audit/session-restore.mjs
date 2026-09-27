import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
export default async function runSessionRestore(api) {
  await api.goto('/system/oauth2/client');
  await api.test('测试收尾：还原隔离库访问令牌寿命', async () => {
    const original = JSON.parse(
      await readFile(join(api.work, 'oauth-default-restore.json'), 'utf8'),
    );
    const response = await api.request(
      '/admin-api/system/oauth2/client/update',
      {
        method: 'PUT',
        data: original,
      },
    );
    api.assert.equal(response.body.code, 0);
  });
}
