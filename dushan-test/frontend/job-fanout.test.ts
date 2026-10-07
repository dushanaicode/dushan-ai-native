import { createApp, nextTick } from 'vue';

import { afterEach, expect, it, vi } from 'vitest';

const state = vi.hoisted(() => ({
  confirm: undefined as (() => Promise<void>) | undefined,
  values: {
    cronExpression: '0 0 * * *',
    fanOut: true,
    handlerName: 'infra.job.clean',
    name: '逐租户任务',
    retryCount: 0,
    retryInterval: 0,
  },
}));
const createJob = vi.hoisted(() => vi.fn());
vi.mock('#/api/infra/job', () => ({
  createJob,
  getJob: vi.fn(),
  updateJob: vi.fn(),
}));
vi.mock('#/adapter/form', () => ({
  useVbenForm: () => [
    { render: () => null },
    {
      getValues: async () => state.values,
      validate: async () => ({ valid: true }),
    },
  ],
}));
vi.mock(
  '../../dushan-admin-frontend/packages/effects/common-ui/src/index.ts',
  () => ({
    useVbenModal: (options: { onConfirm: () => Promise<void> }) => {
      state.confirm = options.onConfirm;
      return [
        { render: () => null },
        { close: vi.fn(), lock: vi.fn(), unlock: vi.fn() },
      ];
    },
  }),
);
vi.mock('#/components', () => ({ CronTab: {}, DictTag: {} }));
vi.mock('#/services/dictionary/context', () => ({ useDictionary: vi.fn() }));
vi.mock('#/locales', () => ({ $t: (key: string) => key }));
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn() },
  ElTimeline: {},
  ElTimelineItem: {},
}));

const { useDetailSchema, useFormSchema } =
  await import('../../dushan-admin-frontend/apps/web-ele/src/views/infra/job/data');
const { default: JobForm } =
  await import('../../dushan-admin-frontend/apps/web-ele/src/views/infra/job/modules/form.vue');

afterEach(() => vi.clearAllMocks());

it('任务表单提供默认关闭的按租户执行开关，详情显示执行范围', () => {
  expect(
    useFormSchema().find((field) => field.fieldName === 'fanOut'),
  ).toMatchObject({
    component: 'Switch',
    defaultValue: false,
    label: '按租户执行',
  });
  const content = useDetailSchema().find(
    (field) => field.field === 'fanOut',
  )!.content!;
  expect(content({ fanOut: true })).toBe('每个有效租户分别执行');
  expect(content({ fanOut: false })).toBe('当前租户');
});

it.each([true, false])('真实表单提交保留 fanOut=%s', async (fanOut) => {
  state.values.fanOut = fanOut;
  const host = document.createElement('div');
  document.body.append(host);
  const app = createApp(JobForm);
  app.mount(host);
  try {
    await nextTick();
    await state.confirm!();
    expect(createJob).toHaveBeenCalledWith(expect.objectContaining({ fanOut }));
  } finally {
    app.unmount();
    host.remove();
  }
});
