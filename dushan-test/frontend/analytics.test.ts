import { afterEach, expect, it } from 'vitest';

import {
  installAnalytics,
  readAnalyticsConfig,
} from '../../dushan-admin-frontend/apps/web-ele/src/services/analytics';

const websiteId = '0f5c1e6a-3b2d-4c8e-9a71-5d6b4e2f1c3a';

afterEach(() => {
  for (const script of document.head.querySelectorAll('script'))
    script.remove();
});

it('统计配置全部留空时关闭，不注入任何脚本', () => {
  const config = readAnalyticsConfig({
    domains: '',
    scriptUrl: '',
    websiteId: '',
  });
  expect(config).toEqual({ enabled: false });
  installAnalytics(config, document);
  expect(document.head.querySelector('script')).toBeNull();
});

it('统计配置不完整或不安全时启动失败，不静默关闭', () => {
  for (const environment of [
    {
      domains: '',
      scriptUrl: 'https://stats.example.org/script.js',
      websiteId,
    },
    {
      domains: 'demo.example.org',
      scriptUrl: 'http://stats.example.org/script.js',
      websiteId,
    },
    {
      domains: 'demo.example.org',
      scriptUrl: 'https://user:pass@stats.example.org/script.js',
      websiteId,
    },
    {
      domains: 'demo.example.org',
      scriptUrl: 'https://stats.example.org/script.js',
      websiteId: 'not-a-uuid',
    },
    {
      domains: 'https://demo.example.org',
      scriptUrl: 'https://stats.example.org/script.js',
      websiteId,
    },
  ])
    expect(() => readAnalyticsConfig(environment)).toThrow(TypeError);
});

it('开启后注入限定域名的 Umami 脚本，并排除查询参数、尊重禁止追踪', () => {
  installAnalytics(
    readAnalyticsConfig({
      domains: 'demo.example.org, www.example.org',
      scriptUrl: 'https://stats.example.org/script.js',
      websiteId,
    }),
    document,
  );
  const script = document.head.querySelector('script')!;
  expect(script.getAttribute('src')).toBe(
    'https://stats.example.org/script.js',
  );
  expect(script.defer).toBe(true);
  expect(
    Object.fromEntries(
      script
        .getAttributeNames()
        .filter((name) => name.startsWith('data-'))
        .map((name) => [name, script.getAttribute(name)]),
    ),
  ).toEqual({
    'data-website-id': websiteId,
    'data-domains': 'demo.example.org,www.example.org',
    'data-do-not-track': 'true',
    'data-exclude-search': 'true',
  });
});
