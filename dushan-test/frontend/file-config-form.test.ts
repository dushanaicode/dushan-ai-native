import { createApp, h, nextTick } from 'vue';

import { expect, it, vi } from 'vitest';

import { initComponentAdapter } from '../../dushan-admin-frontend/apps/web-ele/src/adapter/component';
import {
  initSetupVbenForm,
  useVbenForm,
} from '../../dushan-admin-frontend/apps/web-ele/src/adapter/form';
import { setupI18n } from '../../dushan-admin-frontend/apps/web-ele/src/locales';
import { useFormSchema } from '../../dushan-admin-frontend/apps/web-ele/src/views/infra/fileConfig/data';

vi.mock('#/services/dictionary/context', () => ({
  useDictionary: () => ({ getDictOptions: () => [{ label: 'S3', value: 20 }] }),
}));

it('修改存储桶时凭据可留空，新建配置仍必须填写凭据', async () => {
  await initComponentAdapter();
  await initSetupVbenForm();
  let form!: ReturnType<typeof useVbenForm>[1];
  const app = createApp({
    setup() {
      const [Form, api] = useVbenForm({
        schema: useFormSchema().filter((field) =>
          [
            'id',
            'name',
            'storage',
            'config.endpoint',
            'config.bucket',
            'config.accessKey',
            'config.accessSecret',
            'config.domain',
          ].includes(field.fieldName),
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
  const values = {
    name: 'MinIO',
    storage: 20,
    config: {
      endpoint: 'http://127.0.0.1:9000',
      bucket: 'new-bucket',
      domain: '',
    },
  };
  try {
    await form.setValues({ ...values, id: '10300000040005' });
    await nextTick();
    expect((await form.validate()).valid).toBe(true);
    await form.setValues({ ...values, id: undefined });
    await nextTick();
    expect((await form.validate()).valid).toBe(false);
    await form.setValues({
      ...values,
      id: undefined,
      config: {
        ...values.config,
        accessKey: 'fixture-key',
        accessSecret: 'fixture-secret',
      },
    });
    await nextTick();
    expect((await form.validate()).valid).toBe(true);
  } finally {
    app.unmount();
    container.remove();
  }
});
