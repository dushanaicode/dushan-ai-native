import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

export default async function runAuthMatrix(api) {
  await api.goto('/dashboard/analytics');
  const spec = JSON.parse(
    await readFile(join(api.work, 'openapi.json'), 'utf8'),
  );
  const rows = [];
  const protectedOperations = [];
  for (const [path, operations] of Object.entries(spec.paths)) {
    if (!path.startsWith('/admin-api/')) continue;
    for (const [method, operation] of Object.entries(operations)) {
      if (
        !['delete', 'get', 'patch', 'post', 'put'].includes(method) ||
        operation['x-route-access']?.mode === 'public'
      )
        continue;
      protectedOperations.push({
        path,
        method: method.toUpperCase(),
        operation,
      });
    }
  }
  for (const item of protectedOperations) {
    const allowedCodes = [];
    await api.test(
      `匿名鉴权 ${item.method} ${item.path}`,
      async () => {
        const path = item.path.replaceAll(/\{[^}]+\}/g, '9223372036854775000');
        const result = await api.request(path, {
          method: item.method,
          auth: false,
          credentials: 'omit',
          data: ['PATCH', 'POST', 'PUT'].includes(item.method) ? {} : undefined,
        });
        allowedCodes.push(result.body.code);
        const denied = [
          401, 403, 1_004_001, 1_004_002, 1_004_003, 1_004_004,
        ].includes(result.body.code);
        rows.push({
          method: item.method,
          path: item.path,
          http: result.http,
          code: result.body.code,
          message: result.body.message,
          denied,
          source: 'browser-api-anonymous',
        });
        api.assert(denied, `未按鉴权拒绝返回：${JSON.stringify(rows.at(-1))}`);
        return rows.at(-1);
      },
      { allowedCodes },
    );
  }
  await writeFile(
    join(api.output, 'anonymous-matrix.json'),
    JSON.stringify(rows, null, 2),
  );
}
