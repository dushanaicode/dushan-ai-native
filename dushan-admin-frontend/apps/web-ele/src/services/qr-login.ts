/** UI 入口按设备识别；后端始终按账号会话授权。触屏 Windows PC 不视为手机。 */
export function isMobileWeb(
  userAgent = navigator.userAgent,
  touchPoints = navigator.maxTouchPoints,
) {
  return (
    /Android|iPhone|iPad|iPod/i.test(userAgent) ||
    (/Macintosh/i.test(userAgent) && touchPoints > 1)
  );
}

export function qrLoginUrl(
  href: string,
  origin = import.meta.env.VITE_APP_QR_LOGIN_ORIGIN || window.location.origin,
) {
  return new URL(href, origin).href;
}

export function parseQrLoginUrl(
  value: string,
  scanHref: string,
  origin = window.location.origin,
) {
  const expected = new URL(scanHref, origin);
  const actual = new URL(value);
  if (actual.origin !== expected.origin) throw new Error('invalid QR origin');
  const hashMode = expected.hash.startsWith('#/');
  if (hashMode && (actual.pathname !== expected.pathname || actual.search))
    throw new Error('invalid QR base');
  const target = hashMode ? new URL(actual.hash.slice(1), origin) : actual;
  const route = hashMode ? new URL(expected.hash.slice(1), origin) : expected;
  if (target.pathname !== route.pathname || target.hash)
    throw new Error('invalid QR route');
  const params = target.searchParams;
  if (params.size !== 2) {
    throw new Error('invalid QR parameters');
  }
  const ticket = params.get('ticket');
  const tenantId = params.get('tenantId');
  if (
    ticket === null ||
    tenantId === null ||
    !/^[\w-]{43}$/.test(ticket) ||
    !/^[1-9]\d{0,18}$/.test(tenantId)
  )
    throw new Error('invalid QR ticket');
  return { ticket, tenantId };
}
