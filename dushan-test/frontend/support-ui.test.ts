import { createApp, h, nextTick, ref } from 'vue';

import { afterEach, expect, it, vi } from 'vitest';

import LocalCaptcha from '../../dushan-admin-frontend/apps/web-ele/src/components/captcha/local-captcha.vue';
import UnifiedCaptcha from '../../dushan-admin-frontend/apps/web-ele/src/components/captcha/unified-captcha.vue';
import DocAlert from '../../dushan-admin-frontend/apps/web-ele/src/components/doc-alert.vue';
import DocLinksFooter from '../../dushan-admin-frontend/apps/web-ele/src/components/doc-links-footer.vue';
import NotificationContent from '../../dushan-admin-frontend/apps/web-ele/src/components/notification-content.vue';
import { captchaChallengeSchema } from '../../dushan-admin-frontend/apps/web-ele/src/services/captcha/schema';
import {
  buildDocUrl,
  projectLinks,
  readDocLinkConfig,
} from '../../dushan-admin-frontend/apps/web-ele/src/services/doc-links';

const disposers: Array<() => void> = [];
afterEach(() => {
  for (const dispose of disposers.splice(0)) dispose();
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});
it('弹窗验证成功后销毁挑战子树，不依赖上游弹窗默认缓存', async () => {
  const api = ref<{ verify: () => Promise<unknown> }>();
  const value = {
    token: 'a'.repeat(43),
    purpose: 'login',
    expires_in: 60,
    provider: 'click_word',
    data: {
      width: 320,
      height: 160,
      format: 'jpeg',
      piece_format: 'png',
      coordinates: 'original_pixels',
      image: 'a',
      words: ['甲', '乙', '丙'],
    },
  };
  const certificate = {
    verification: 'v'.repeat(43),
    purpose: 'login',
    expires_in: 30,
  };
  mount(() =>
    h(UnifiedCaptcha, {
      ref: api,
      purpose: 'login',
      ports: {
        configuration: async () => ({
          enabled: true,
          provider: 'click_word',
          purposes: ['login'],
        }),
        challenge: async () => value,
        check: async () => certificate,
      },
    }),
  );
  const flow = api.value!.verify();
  await vi.waitFor(() =>
    expect(document.querySelector('[role="dialog"] img')).not.toBeNull(),
  );
  const image = document.querySelector<HTMLImageElement>(
    '[role="dialog"] img',
  )!;
  vi.spyOn(image, 'getBoundingClientRect').mockReturnValue(
    new DOMRect(0, 0, 320, 160),
  );
  for (let i = 0; i < 3; i++)
    image.dispatchEvent(
      new MouseEvent('click', { bubbles: true, clientX: 10, clientY: 10 }),
    );
  await expect(flow).resolves.toEqual(certificate);
  await nextTick();
  expect(document.querySelector('[role="dialog"] [role="region"]')).toBeNull();
});
function mount(render: () => ReturnType<typeof h>) {
  const container = document.createElement('div');
  document.body.append(container);
  const app = createApp({ render });
  const errors: unknown[] = [];
  app.config.errorHandler = (error) => errors.push(error);
  app.mount(container);
  disposers.push(() => {
    app.unmount();
    container.remove();
  });
  return { container, errors };
}
it('通知详情保留正文，剔除脚本、事件属性、危险链接和 iframe', async () => {
  const content =
    '<p onclick="alert(1)">正文<strong>加粗</strong><a href="javascript:alert(1)">链接</a></p><script>alert(1)</script><iframe src="about:blank"></iframe><img src="about:blank" onerror="alert(1)">';
  const { container, errors } = mount(() =>
    h(NotificationContent, { content }),
  );
  await vi.waitFor(() =>
    expect(container.querySelector('.tiptap strong')?.textContent).toBe('加粗'),
  );
  expect(
    container.querySelector(
      'script, iframe, [onclick], [onerror], [href^="javascript:"]',
    ),
  ).toBeNull();
  expect(
    container.querySelector('.tiptap')?.getAttribute('contenteditable'),
  ).toBe('false');
  expect(errors).toEqual([]);
});
function stubDocEnv(alert: string, docSite: string, deepDive: string) {
  vi.stubEnv('VITE_DOC_ALERT_ENABLED', alert);
  vi.stubEnv('VITE_DOC_SITE_URL', docSite);
  vi.stubEnv('VITE_DEEP_DIVE_SITE_URL', deepDive);
}
const docEntry = {
  title: '定时任务',
  guidePath: 'modules/infra/job',
  deepDivePath: 'infra/job',
};
it('文档地址只接受 HTTP(S) 站点根，站内路径附加 UTM 且不带用户信息', () => {
  const config = readDocLinkConfig({
    alertEnabled: 'true',
    docSiteUrl: 'https://docs.example.org/native',
    deepDiveSiteUrl: '',
  });
  expect(config.deepDiveSite).toBeUndefined();
  const href = new URL(
    buildDocUrl(config.docSite!, 'modules/infra/job', {
      channel: 'doc_alert',
      content: 'modules/infra/job',
    }),
  );
  expect(href.origin + href.pathname).toBe(
    'https://docs.example.org/native/modules/infra/job',
  );
  expect(Object.fromEntries(href.searchParams)).toEqual({
    utm_source: 'dushan-ai-native',
    utm_medium: 'admin',
    utm_campaign: 'doc_alert',
    utm_content: 'modules/infra/job',
  });
  for (const docSiteUrl of [
    'javascript:alert(1)',
    'https://user:pass@docs.example.org',
    'https://docs.example.org/?a=1',
  ])
    expect(() =>
      readDocLinkConfig({
        alertEnabled: 'true',
        docSiteUrl,
        deepDiveSiteUrl: '',
      }),
    ).toThrow(TypeError);
  expect(() =>
    readDocLinkConfig({
      alertEnabled: '1',
      docSiteUrl: '',
      deepDiveSiteUrl: '',
    }),
  ).toThrow(TypeError);
  for (const path of ['/root', '../up', 'https://evil.example'])
    expect(() =>
      buildDocUrl(config.docSite!, path, { channel: 'login', content: path }),
    ).toThrow(TypeError);
});
it('登录页链接只显示已配置站点，项目仓库始终可达', () => {
  stubDocEnv('true', '', '');
  const plain = mount(() => h(DocLinksFooter));
  expect(
    [...plain.container.querySelectorAll('a')].map((link) => link.href),
  ).toEqual([projectLinks.github, projectLinks.mirror]);
  stubDocEnv('true', 'https://docs.example.org', 'https://zsxq.example.org');
  const full = mount(() => h(DocLinksFooter));
  const hrefs = [...full.container.querySelectorAll('a')].map(
    (link) => new URL(link.href),
  );
  expect(hrefs.map((url) => url.host)).toEqual([
    'docs.example.org',
    'zsxq.example.org',
    'github.com',
    new URL(projectLinks.mirror).host,
  ]);
  expect(hrefs[0]!.searchParams.get('utm_campaign')).toBe('login');
  expect(full.errors).toEqual([]);
});
it('文档提示关闭或未配置文档站时不渲染，开启后展示免费文档与源码解读并可关闭', async () => {
  stubDocEnv('false', 'https://docs.example.org', '');
  const hidden = mount(() => h(DocAlert, { entry: docEntry }));
  expect(hidden.container.querySelector('[role="alert"]')).toBeNull();
  stubDocEnv('true', '', 'https://zsxq.example.org');
  const noSite = mount(() => h(DocAlert, { entry: docEntry }));
  expect(noSite.container.querySelector('[role="alert"]')).toBeNull();
  expect([...hidden.errors, ...noSite.errors]).toEqual([]);
  stubDocEnv('true', 'https://docs.example.org', '');
  const guideOnly = mount(() => h(DocAlert, { entry: docEntry }));
  expect(guideOnly.container.querySelectorAll('a')).toHaveLength(1);
  stubDocEnv('true', 'https://docs.example.org', 'https://zsxq.example.org');
  const shown = mount(() => h(DocAlert, { entry: docEntry }));
  const links = [...shown.container.querySelectorAll('a')];
  expect(links.map((link) => new URL(link.href).pathname)).toEqual([
    '/modules/infra/job',
    '/infra/job',
  ]);
  expect(links.every((link) => link.rel === 'noopener noreferrer')).toBe(true);
  shown.container.querySelector<HTMLElement>('.el-alert__close-btn')!.click();
  await nextTick();
  await vi.waitFor(() =>
    expect(
      shown.container.querySelector<HTMLElement>('[role="alert"]')?.style
        .display,
    ).toBe('none'),
  );
});
it('点选复用组件只提交提示数量，移除 i 和 t，重复点击不追加', async () => {
  const challenge = captchaChallengeSchema.parse({
    token: 'a'.repeat(43),
    purpose: 'login',
    expires_in: 60,
    provider: 'click_word',
    data: {
      width: 320,
      height: 160,
      format: 'jpeg',
      piece_format: 'png',
      coordinates: 'original_pixels',
      image: 'a',
      words: ['甲', '乙', '丙'],
    },
  });
  const answer = vi.fn();
  const { container } = mount(() =>
    h(LocalCaptcha, {
      challenge: challenge as Extract<
        typeof challenge,
        { provider: 'click_word' }
      >,
      busy: false,
      onAnswer: answer,
    }),
  );
  const image = container.querySelector('img')!;
  vi.spyOn(image, 'getBoundingClientRect').mockReturnValue(
    new DOMRect(0, 0, 320, 160),
  );
  for (let i = 0; i < 4; i++)
    image.dispatchEvent(
      new MouseEvent('click', { bubbles: true, clientX: 10, clientY: 10 }),
    );
  await nextTick();
  expect(answer).toHaveBeenCalledTimes(1);
  expect(answer.mock.calls[0]![0]).toEqual({
    points: [
      { x: 10, y: 10 },
      { x: 10, y: 10 },
      { x: 10, y: 10 },
    ],
  });
});
