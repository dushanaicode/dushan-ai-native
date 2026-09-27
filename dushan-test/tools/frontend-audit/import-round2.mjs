import { writeFile } from 'node:fs/promises';
import { join } from 'node:path';

export default async function runImportRound2(api) {
  await api.goto('/system/user');
  const outputs = [];
  for (const [name, file, update, field] of [
    ['有效初始密码下导入新用户', 'user-import.xlsx', false, 'createUsernames'],
    ['重复导入不覆盖', 'user-import.xlsx', false, 'failureUsernames'],
    ['允许更新后导入', 'user-import-update.xlsx', true, 'updateUsernames'],
  ]) {
    const outcome = await api.test(`导入 API：${name}`, async () => {
      const response = await api.upload(
        '/admin-api/system/user/import',
        join(api.work, file),
        {
          updateSupport: update,
        },
      );
      outputs.push({ name, response });
      await writeFile(
        join(api.output, 'imports.json'),
        JSON.stringify(outputs, null, 2),
      );
      api.assert.equal(response.body.code, 0);
      if (field === 'failureUsernames')
        api.assert(response.body.data[field].qaimport);
      else api.assert(response.body.data[field].includes('qaimport'));
    });
    if (outcome.status === 'failed') break;
  }
}
