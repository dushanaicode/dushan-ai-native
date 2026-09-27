import { createApp, h, nextTick } from 'vue';
import { expect, it, vi } from 'vitest';
import { initComponentAdapter } from '../../dushan-admin-frontend/apps/web-ele/src/adapter/component';
import {
  initSetupVbenForm,
  useVbenForm,
} from '../../dushan-admin-frontend/apps/web-ele/src/adapter/form';
import { setupI18n } from '../../dushan-admin-frontend/apps/web-ele/src/locales';
import { useFormSchema } from '../../dushan-admin-frontend/apps/web-ele/src/views/infra/dataSourceConfig/data';

vi.mock('#/services/dictionary/context', () => ({
  useDictionary: () => ({ getDictOptions: () => [] }),
}));

it('编辑脱敏连接时可留空保留，新建仍必须填写URL', async () => {
  await initComponentAdapter();
  await initSetupVbenForm();
  let form!: ReturnType<typeof useVbenForm>[1];
  const app = createApp({
    setup() {
      const [Form, api] = useVbenForm({
        schema: useFormSchema().filter((field) =>
          ['id', 'name', 'dbType', 'url'].includes(field.fieldName),
        ),
        showDefaultActions: false,
      });
      form = api;
      return () => h(Form);
    },
  });
  await setupI18n(app);
  const container = document.createElement('div');
  document.body.append(container);
  app.mount(container);
  try {
    await form.setValues({ id: '10300000060001', name: 'Source', url: '' });
    await nextTick();
    expect((await form.validate()).valid).toBe(true);
    await form.setValues({
      dbType: 'tidb',
      url: 'mysql+aiomysql://fixture@127.0.0.1:4000/demo',
    });
    await nextTick();
    expect((await form.validate()).valid).toBe(true);
    expect((await form.getValues()).dbType).toBe('tidb');
    await form.setValues({ id: '10300000060002', dbType: 'tidb', url: '' });
    await nextTick();
    expect((await form.validate()).valid).toBe(true);
    expect((await form.getValues()).dbType).toBe('tidb');
    expect(
      container.querySelector('.data-source-url .el-select')!.textContent,
    ).toContain('TiDB');
    await form.setValues({
      dbType: 'oracle',
      url: 'oracle+oracledb://a:b@db:1521/demo',
    });
    await nextTick();
    expect((await form.validate()).valid).toBe(false);
    await form.setValues({ id: undefined, name: 'Source', url: '' });
    await nextTick();
    expect((await form.validate()).valid).toBe(false);
    await form.setValues({
      url: 'mysql+aiomysql://fixture@127.0.0.1:3306/demo',
    });
    await nextTick();
    expect((await form.validate()).valid).toBe(true);
  } finally {
    app.unmount();
    container.remove();
  }
});
