import assert from 'node:assert/strict';
import { Buffer } from 'node:buffer';
import { execFileSync } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import process from 'node:process';
import { pathToFileURL } from 'node:url';

const work = resolve('Temp/qr-login-production/browser');
const server = JSON.parse(await readFile(`${work}/server.json`, 'utf8'));
const { chromium } = await import(
  pathToFileURL(process.env.PLAYWRIGHT_ENTRY).href
);
const require = createRequire(
  new URL(
    '../../dushan-admin-frontend/apps/web-ele/package.json',
    import.meta.url,
  ),
);
const jsQR = require('jsqr');
const origin = `http://localhost:${server.webPort}`;
const hashHistory = process.env.DUSHAN_QR_HISTORY === 'hash';
const routeUrl = (path) => `${origin}${hashHistory ? '/#' : ''}${path}`;
const contexts = [];
const errors = [];
const checked = [];
await mkdir(`${work}/runtime`, { recursive: true });

async function context(name, mobile = false) {
  const result = await chromium.launchPersistentContext(
    `${work}/${name}-profile`,
    {
      channel: 'chrome',
      chromiumSandbox: true,
      headless: true,
      viewport: mobile
        ? { width: 390, height: 844 }
        : { width: 1440, height: 980 },
      ...(mobile
        ? {
            isMobile: true,
            hasTouch: true,
            userAgent:
              'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1',
            args: [
              '--use-fake-device-for-media-stream',
              '--use-fake-ui-for-media-stream',
              `--use-file-for-fake-video-capture=${work}/runtime/camera.y4m`,
            ],
          }
        : {}),
    },
  );
  contexts.push(result);
  await result.clearCookies();
  await result.addInitScript((run) => {
    if (sessionStorage.getItem('qr-qa-run') === run) return;
    localStorage.clear();
    sessionStorage.clear();
    sessionStorage.setItem('qr-qa-run', run);
  }, `${name}-${Date.now()}`);
  const page = result.pages()[0];
  page.setDefaultTimeout(30000);
  page.on('pageerror', (error) => errors.push(error.message));
  return { page, context: result };
}

async function code(page) {
  const image = page.locator('img[alt="扫码登录"]');
  await image.waitFor({ state: 'visible' });
  await page.waitForFunction(
    () => document.querySelector('img[alt="扫码登录"]')?.naturalWidth > 0,
  );
  const pixels = await image.evaluate((img) => {
    const canvas = document.createElement('canvas');
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, 0);
    return {
      rgba: [...ctx.getImageData(0, 0, canvas.width, canvas.height).data],
      width: canvas.width,
      height: canvas.height,
      png: img.src.split(',')[1],
    };
  });
  const decoded = jsQR(
    new Uint8ClampedArray(pixels.rgba),
    pixels.width,
    pixels.height,
  );
  assert.ok(decoded);
  assert.ok(decoded.data.startsWith(`${routeUrl('/auth/qr-scan')}?`));
  await writeFile(`${work}/runtime/qr.png`, Buffer.from(pixels.png, 'base64'));
  return decoded.data;
}

function video() {
  execFileSync(
    resolve('../dushan-admin-backend/.venv/Scripts/python.exe'),
    [
      '-B',
      '-c',
      `
from pathlib import Path
from PIL import Image
root=Path(r'${work.replaceAll('\\', '/')}')/'runtime'
qr=Image.open(root/'qr.png').convert('RGB')
image=Image.new('RGB',(640,480),'white')
image.paste(qr,((640-qr.width)//2,(480-qr.height)//2))
y,u,v=image.convert('YCbCr').split()
frame=y.tobytes()+u.resize((320,240)).tobytes()+v.resize((320,240)).tobytes()
with (root/'camera.y4m').open('wb') as stream:
    stream.write(b'YUV4MPEG2 W640 H480 F10:1 Ip A1:1 C420jpeg\\n')
    for _ in range(30): stream.write(b'FRAME\\n'+frame)
`,
    ],
    { cwd: process.cwd(), env: process.env },
  );
}

function passed(name) {
  checked.push(name);
  console.log(`PASS ${name}`);
}

try {
  const { page: desktop } = await context('desktop');
  await desktop.goto(routeUrl('/auth/login'), { timeout: 60000 });
  await desktop.getByRole('button', { name: '扫码登录', exact: true }).click();
  const firstCode = await code(desktop);
  video();
  await desktop.screenshot({ path: `${work}/desktop-qr.png`, fullPage: true });
  passed('PC login displays a real same-origin QR code');

  const { page: phone } = await context('phone', true);
  await phone.goto(firstCode, { timeout: 60000 });
  await phone.getByPlaceholder('请输入用户名', { exact: true }).fill('admin');
  assert.equal(
    await phone.getByRole('button', { name: '扫码登录', exact: true }).count(),
    0,
  );
  await phone.locator('input[type="password"]').fill('admin123');
  await phone.getByRole('button', { name: 'login', exact: true }).click();
  await phone
    .getByRole('button', { name: '确认登录', exact: true })
    .waitFor({ state: 'visible' });
  await desktop.getByText('已扫码，请在手机上确认', { exact: true }).waitFor();
  await phone.screenshot({ path: `${work}/phone-confirm.png`, fullPage: true });
  passed('Unauthenticated phone signs in and returns to confirmation');
  const consumed = desktop.waitForResponse((response) =>
    response.url().endsWith('/qr-login/consume'),
  );
  await phone.getByRole('button', { name: '确认登录', exact: true }).click();
  const reply = await (await consumed).json();
  assert.equal(reply.code, 0);
  assert.equal(reply.data.tenantId, '1');
  assert.equal(Object.hasOwn(reply.data, 'refreshToken'), false);
  await desktop.waitForURL(
    (url) =>
      !(hashHistory ? url.hash.slice(1) : url.pathname).startsWith('/auth/'),
  );
  passed('Phone approval creates the PC session and loads permissions');
  await desktop.goto(routeUrl('/profile'));
  await desktop.getByText('基本信息', { exact: true }).waitFor();
  assert.equal(
    await desktop.getByRole('button', { name: '扫一扫', exact: true }).count(),
    0,
  );
  passed('PC profile hides the scanner');

  await phone
    .getByRole('button', { name: '返回个人中心', exact: true })
    .click();
  await phone.getByRole('button', { name: '扫一扫', exact: true }).waitFor();
  await phone.reload();
  await phone.getByRole('button', { name: '扫一扫', exact: true }).waitFor();
  passed('Phone login persists across page reloads');
  await phone.getByRole('button', { name: '扫一扫', exact: true }).click();
  const { page: nextDesktop } = await context('desktop-second');
  await nextDesktop.goto(routeUrl('/auth/qrcode-login'));
  await code(nextDesktop);
  video();
  await phone.getByRole('button', { name: '扫一扫', exact: true }).click();
  await phone.getByRole('button', { name: '确认登录', exact: true }).waitFor();
  assert.equal(
    await phone.locator('video').evaluate((element) => element.srcObject),
    null,
  );
  passed('Phone profile scanner decodes camera frames and releases the camera');
  await phone.getByRole('button', { name: '取消登录', exact: true }).click();
  await nextDesktop
    .getByText('登录已取消，可刷新二维码重新尝试', { exact: true })
    .waitFor();
  passed('Cancellation does not log in the PC');
  assert.deepEqual(errors, []);
  await writeFile(
    `${work}/result.json`,
    JSON.stringify({ checked, pageErrors: errors }, null, 2),
  );
  console.log(JSON.stringify({ checked, pageErrors: errors }));
} catch (error) {
  for (let index = 0; index < contexts.length; index++) {
    const page = contexts[index].pages()[0];
    if (!page) continue;
    await page.screenshot({
      path: `${work}/failure-${index}.png`,
      fullPage: true,
    });
    await writeFile(
      `${work}/failure-${index}.txt`,
      await page.locator('body').innerText(),
    );
  }
  throw error;
} finally {
  for (const item of contexts) await item.close();
}
