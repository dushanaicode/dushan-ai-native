import { beforeEach, describe, expect, it, vi } from 'vitest';

import { exportApiAccessLog } from '../../dushan-admin-frontend/apps/web-ele/src/api/infra/api-access-log/index';
import { exportApiErrorLog } from '../../dushan-admin-frontend/apps/web-ele/src/api/infra/api-error-log/index';
import { exportConfigData } from '../../dushan-admin-frontend/apps/web-ele/src/api/infra/config/data/index';
import { getSimpleConfigTypeList } from '../../dushan-admin-frontend/apps/web-ele/src/api/infra/config/type';
import { exportConfigType } from '../../dushan-admin-frontend/apps/web-ele/src/api/infra/config/type/index';
import { exportDataSourceConfig } from '../../dushan-admin-frontend/apps/web-ele/src/api/infra/data-source-config/index';
import { exportJob } from '../../dushan-admin-frontend/apps/web-ele/src/api/infra/job/index';
import { exportJobLog } from '../../dushan-admin-frontend/apps/web-ele/src/api/infra/job/log/index';
import { exportMq } from '../../dushan-admin-frontend/apps/web-ele/src/api/infra/mq/index';
import { exportMqLog } from '../../dushan-admin-frontend/apps/web-ele/src/api/infra/mq/log/index';
import { exportDictData } from '../../dushan-admin-frontend/apps/web-ele/src/api/system/dict/data/index';
import { getSimpleDictTypeList } from '../../dushan-admin-frontend/apps/web-ele/src/api/system/dict/type';
import { exportDictType } from '../../dushan-admin-frontend/apps/web-ele/src/api/system/dict/type/index';
import { exportLoginLog } from '../../dushan-admin-frontend/apps/web-ele/src/api/system/logger/loginlog/index';
import { exportOperateLog } from '../../dushan-admin-frontend/apps/web-ele/src/api/system/logger/operatelog/index';
import { exportMailAccount } from '../../dushan-admin-frontend/apps/web-ele/src/api/system/mail/account/index';
import { exportMailLog } from '../../dushan-admin-frontend/apps/web-ele/src/api/system/mail/log/index';
import { exportMailTemplate } from '../../dushan-admin-frontend/apps/web-ele/src/api/system/mail/template/index';
import { exportPost } from '../../dushan-admin-frontend/apps/web-ele/src/api/system/post/index';
import { exportRole } from '../../dushan-admin-frontend/apps/web-ele/src/api/system/role/index';
import { exportSmsLog } from '../../dushan-admin-frontend/apps/web-ele/src/api/system/sms/log/index';
import { exportSmsTemplate } from '../../dushan-admin-frontend/apps/web-ele/src/api/system/sms/template/index';
import { exportTenant } from '../../dushan-admin-frontend/apps/web-ele/src/api/system/tenant/index';
import { exportTenantPackage } from '../../dushan-admin-frontend/apps/web-ele/src/api/system/tenant/package/index';
import { exportUser } from '../../dushan-admin-frontend/apps/web-ele/src/api/system/user/index';

const client = vi.hoisted(() => ({ download: vi.fn(), get: vi.fn() }));
vi.mock('#/api/request', () => ({ requestClient: client }));

beforeEach(() => {
  vi.clearAllMocks();
});

describe('导出 API 查询契约', () => {
  it.each([
    ['/infra/logger/api-access-log/export-excel', exportApiAccessLog],
    ['/infra/logger/api-error-log/export-excel', exportApiErrorLog],
    ['/infra/config/export-excel', exportConfigData],
    ['/infra/config/type/export-excel', exportConfigType],
    ['/infra/data-source/export-excel', exportDataSourceConfig],
    ['/infra/job/export-excel', exportJob],
    ['/infra/job/log/export-excel', exportJobLog],
    ['/infra/mq/export-excel', exportMq],
    ['/infra/mq/log/export-excel', exportMqLog],
    ['/system/dict/data/export-excel', exportDictData],
    ['/system/dict/type/export-excel', exportDictType],
    ['/system/logger/login-log/export-excel', exportLoginLog],
    ['/system/logger/operate-log/export-excel', exportOperateLog],
    ['/system/mail/account/export-excel', exportMailAccount],
    ['/system/mail/log/export-excel', exportMailLog],
    ['/system/mail/template/export-excel', exportMailTemplate],
    ['/system/dept/post/export-excel', exportPost],
    ['/system/permission/role/export-excel', exportRole],
    ['/system/sms/log/export-excel', exportSmsLog],
    ['/system/sms/template/export-excel', exportSmsTemplate],
    ['/system/tenant/export-excel', exportTenant],
    ['/system/tenant/package/export-excel', exportTenantPackage],
    ['/system/user/export-excel', exportUser],
  ])('%s 使用重复键传递导出字段', async (url, exportApi) => {
    const params = { fields: ['id', 'create_time'] };
    const file = new Blob(['excel']);
    client.download.mockResolvedValueOnce(file);

    expect(await exportApi(params)).toBe(file);
    expect(client.download).toHaveBeenCalledExactlyOnceWith(url, {
      params,
      paramsSerializer: 'repeat',
    });
  });

  it('字典和配置类型精简列表使用统一路径，配置模块筛选保留', async () => {
    await getSimpleDictTypeList();
    await getSimpleConfigTypeList('system');

    expect(client.get.mock.calls).toEqual([
      ['/system/dict/type/simple-list'],
      ['/infra/config/type/simple-list', { params: { module: 'system' } }],
    ]);
  });
});
