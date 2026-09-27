import { afterEach, expect, it, vi } from 'vitest';

import {
  isMobileWeb,
  parseQrLoginUrl,
  qrLoginUrl,
} from '../../dushan-admin-frontend/apps/web-ele/src/services/qr-login';

afterEach(() => vi.unstubAllEnvs());

it.each([
  ['Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)', 5, true],
  ['Mozilla/5.0 (Linux; Android 15)', 5, true],
  ['Mozilla/5.0 (Macintosh; Intel Mac OS X)', 5, true],
  ['Mozilla/5.0 (Macintosh; Intel Mac OS X)', 0, false],
  ['Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 10, false],
])('设备识别 %s', (ua, touches, expected) => {
  expect(isMobileWeb(ua, touches)).toBe(expected);
});

const ticket = 'a'.repeat(43);
it('本机电脑二维码使用配置的手机可访问地址，手机仍只接受本站二维码', () => {
  vi.stubEnv('VITE_APP_QR_LOGIN_ORIGIN', 'http://192.168.1.10:5777');
  const href = `/console/#/auth/qr-scan?ticket=${ticket}&tenantId=1`;
  const url = qrLoginUrl(href);
  expect(url).toBe(`http://192.168.1.10:5777${href}`);
  expect(
    parseQrLoginUrl(url, '/console/#/auth/qr-scan', 'http://192.168.1.10:5777'),
  ).toEqual({ ticket, tenantId: '1' });
  expect(() =>
    parseQrLoginUrl(url, '/console/#/auth/qr-scan', 'https://another.example'),
  ).toThrow('invalid QR origin');
});

it('未配置手机入口时沿用当前站点地址', () => {
  vi.stubEnv('VITE_APP_QR_LOGIN_ORIGIN', '');
  expect(qrLoginUrl('/auth/qr-scan')).toBe(
    `${window.location.origin}/auth/qr-scan`,
  );
});
it.each(['/auth/qr-scan', '/console/auth/qr-scan', '/console/#/auth/qr-scan'])(
  '保留端口及部署路径 %s',
  (href) => {
    const url = qrLoginUrl(
      `${href}?ticket=${ticket}&tenantId=9223372036854775807`,
      'https://demo.example:7443',
    );
    expect(url.startsWith('https://demo.example:7443/')).toBe(true);
    expect(parseQrLoginUrl(url, href, 'https://demo.example:7443')).toEqual({
      ticket,
      tenantId: '9223372036854775807',
    });
  },
);

it.each([
  `https://evil.example/auth/qr-scan?ticket=${ticket}&tenantId=1`,
  `https://demo.example:7443/profile?ticket=${ticket}&tenantId=1`,
  `https://demo.example:7443/auth/qr-scan?ticket=${ticket}&ticket=${ticket}&tenantId=1`,
  `https://demo.example:7443/auth/qr-scan?ticket=${ticket}&tenantId=01`,
  `https://demo.example:7443/auth/qr-scan?ticket=short&tenantId=1`,
  `https://demo.example:7443/auth/qr-scan?ticket=${ticket}&tenantId=1&redirect=https://evil.example`,
  `javascript:alert(1)`,
])('拒绝外站、其他路由及非法扫码参数 %s', (url) => {
  expect(() =>
    parseQrLoginUrl(url, '/auth/qr-scan', 'https://demo.example:7443'),
  ).toThrow(/invalid QR/);
});
