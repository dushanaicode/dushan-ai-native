import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

export default async function runSessionTtl(api) {
  await api.goto('/system/oauth2/client');
  await api.test('测试准备：为隔离库新会话设置短访问令牌寿命', async () => {
    const result = await api.request(
      '/admin-api/system/oauth2/client/page?page=1&pageSize=20',
    );
    const client = result.body.data.items.find(
      (item) => item.clientId === 'default',
    );
    const openapi = JSON.parse(
      await readFile(join(api.work, 'openapi.json'), 'utf8'),
    );
    const ref = openapi.paths[
      '/admin-api/system/oauth2/client/update'
    ].put.requestBody.content['application/json'].schema.$ref
      .split('/')
      .at(-1);
    const fields = Object.keys(openapi.components.schemas[ref].properties);
    const original = Object.fromEntries(
      fields
        .filter((key) => key !== 'secret' && key in client)
        .map((key) => [key, client[key]]),
    );
    await writeFile(
      join(api.work, 'oauth-default-restore.json'),
      JSON.stringify(original, null, 2),
    );
    const changed = await api.request(
      '/admin-api/system/oauth2/client/update',
      {
        method: 'PUT',
        data: { ...original, accessTokenValiditySeconds: 20 },
      },
    );
    api.assert.equal(changed.body.code, 0);
  });
}
