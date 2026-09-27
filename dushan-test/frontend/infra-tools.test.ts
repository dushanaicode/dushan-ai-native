import { createApp, h } from 'vue';
import { expect, it } from 'vitest';
import { parse, compileScript, compileTemplate } from '../../dushan-admin-frontend/node_modules/vue/compiler-sfc/index.js';
import { setupFormCreate } from '../../dushan-admin-frontend/apps/web-ele/src/components/form-create/setup';
import { createVueForm } from '../../dushan-admin-frontend/apps/web-ele/src/views/infra/build/export';

it('生成的Vue表单可编译，完整保留引号、换行和script结束标签', () => {
  const title = '姓名 "渡山"\\路径\n</script><script>测试</script>';
  const rules = [{ type: 'input', field: 'name', title, value: 'O\'Brien' }];
  const source = createVueForm(rules, { form: { labelWidth: '120px' }, submitBtn: false });
  const { descriptor, errors } = parse(source);
  expect(errors).toEqual([]);
  const script = compileScript(descriptor, { id: 'generated-form' });
  expect(script.bindings).toMatchObject({ rule: 'setup-ref', option: 'setup-ref', values: 'setup-ref' });
  expect(compileTemplate({ source: descriptor.template!.content, id: 'generated-form', filename: 'GeneratedForm.vue' }).errors).toEqual([]);
  const literal = source.match(/const rule = ref\(formCreate.parseJson\((.+)\)\);/)![1]!;
  expect(JSON.parse(JSON.parse(literal))).toEqual(rules);
  expect(source.match(/<\/script>/g)).toHaveLength(1);
});

it('设计器安装保持Vben加载指令，并注册Native字段供画布和预览使用', () => {
  const app = createApp({ render: () => h('div') });
  const loading = { mounted() {} };
  app.directive('loading', loading);
  setupFormCreate(app);
  setupFormCreate(app);
  expect(app.directive('loading')).toBe(loading);
  for (const name of ['NativeUserSelect', 'NativeDeptSelect', 'NativeDictSelect', 'NativeApiSelect', 'NativeFileUpload', 'NativeImageUpload', 'NativeImagesUpload', 'NativeRichText']) {
    expect(app.component(name)).toBeDefined();
  }
});
