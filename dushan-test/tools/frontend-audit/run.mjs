import assert from 'node:assert/strict';
import { Buffer } from 'node:buffer';
import { existsSync } from 'node:fs';
import { appendFile, mkdir, readFile, writeFile } from 'node:fs/promises';
import {
  basename,
  dirname,
  isAbsolute,
  join,
  relative,
  resolve,
} from 'node:path';
import process from 'node:process';
import { fileURLToPath, pathToFileURL } from 'node:url';

const work = resolve(process.env.DUSHAN_AUDIT_WORKDIR);
const within = relative(resolve('Temp'), work);
assert.ok(within && !isAbsolute(within) && !within.startsWith('..'));
const server = JSON.parse(
  await readFile(
    process.env.DUSHAN_AUDIT_SERVER || join(work, 'server.json'),
    'utf8',
  ),
);
const { chromium } = await import(
  pathToFileURL(process.env.PLAYWRIGHT_ENTRY).href
);
const phase = process.argv[2];
const evidencePhase = process.argv[3] || phase;
const output = join(work, 'browser', evidencePhase);
await mkdir(output, { recursive: true });
const channel = process.env.DUSHAN_AUDIT_BROWSER || 'chrome';
let profileName = process.env.DUSHAN_AUDIT_PROFILE;
if (!profileName) {
  profileName = channel === 'chrome' ? 'production' : channel;
  if (process.env.DUSHAN_AUDIT_SERVER) profileName = 'development';
}
assert.ok(/^[a-z0-9-]+$/.test(profileName));
const context = await chromium.launchPersistentContext(
  join(work, `browser/${profileName}-profile`),
  {
    channel,
    chromiumSandbox: true,
    headless: true,
    acceptDownloads: true,
    downloadsPath: join(work, 'browser/downloads'),
    viewport: { width: 1600, height: 1000 },
  },
);
const page = context.pages()[0];
context.on('close', () =>
  process.stdout.write('AUDIT_BROWSER_CONTEXT_CLOSED\n'),
);
page.on('close', () => process.stdout.write('AUDIT_PAGE_CLOSED\n'));
page.on('crash', () => process.stdout.write('AUDIT_PAGE_CRASHED\n'));
page.setDefaultTimeout(8000);
page.setDefaultNavigationTimeout(25_000);
const calls = [];
const errors = [];
const results = [];
let currentCase = 'startup';
let authorization;
let requestSource = 'ui';
const requestSources = new WeakMap();
const pending = new Set();
const activeRequests = new Set();
let lastNetworkActivity = Date.now();
const productRequest = (request) =>
  /^\/(admin-api|api|weapp-api)\//.test(new URL(request.url()).pathname);
page.on('request', (request) => {
  requestSources.set(request, requestSource);
  if (productRequest(request)) {
    activeRequests.add(request);
    lastNetworkActivity = Date.now();
  }
  const token = request.headers().authorization;
  if (token && requestSource === 'ui') authorization = token;
});
for (const event of ['requestfinished', 'requestfailed']) {
  page.on(event, (request) => {
    if (activeRequests.delete(request)) lastNetworkActivity = Date.now();
  });
}

async function settle() {
  await page.waitForTimeout(150);
  const deadline = Date.now() + 20_000;
  while (activeRequests.size > 0 || Date.now() - lastNetworkActivity < 150) {
    assert.ok(Date.now() < deadline, '业务接口等待超时');
    await page.waitForTimeout(50);
  }
  await Promise.all(pending);
}

function safeUrl(value) {
  const url = new URL(value);
  for (const key of [...url.searchParams.keys()]) {
    if (/token|ticket|code|state|secret|password/i.test(key))
      url.searchParams.set(key, '[redacted]');
  }
  return url.pathname + url.search;
}
page.on('pageerror', (error) =>
  errors.push({ case: currentCase, message: error.message }),
);
page.on('console', (message) => {
  if (
    message.type() === 'error' &&
    /^(ZodError|TypeError|ReferenceError|SyntaxError):/.test(message.text())
  ) {
    errors.push({ case: currentCase, message: message.text().split('\n')[0] });
  }
});
page.on('response', (response) => {
  if (
    !response.url().includes('/admin-api/') &&
    !response.url().includes('/api/ws')
  )
    return;
  const record = {
    case: currentCase,
    source: requestSources.get(response.request()),
    method: response.request().method(),
    url: safeUrl(response.url()),
    http: response.status(),
  };
  calls.push(record);
  const promise = (async () => {
    if (response.headers()['content-type']?.includes('application/json')) {
      try {
        const body = await response.json();
        record.code = body.code;
        record.message = body.message;
        if (
          response.url().endsWith('/auth/login') &&
          body.code === 0 &&
          record.source === 'ui'
        )
          authorization = `Bearer ${body.data.accessToken}`;
        if (
          response.url().includes('/auth/get-permission-info') &&
          body.code === 0 &&
          !existsSync(join(work, 'menus.json'))
        ) {
          await writeFile(
            join(work, 'menus.json'),
            JSON.stringify(body.data.menus, null, 2),
          );
        }
      } catch (error) {
        record.readError = error.message.split('\n')[0];
      }
    }
  })();
  pending.add(promise);
  promise.finally(() => pending.delete(promise));
});

async function test(name, operation, { allowedCodes = [] } = {}) {
  if (
    process.env.DUSHAN_AUDIT_CASE_FILTER &&
    !new RegExp(process.env.DUSHAN_AUDIT_CASE_FILTER).test(name)
  )
    return { status: 'not-run' };
  currentCase = name;
  const started = Date.now();
  const firstCall = calls.length;
  const firstError = errors.length;
  const entry = {
    name,
    status: 'passed',
    started: new Date(started).toISOString(),
  };
  try {
    entry.detail = await operation();
    await Promise.all(pending);
    const caseCalls = calls.slice(firstCall);
    const failures = caseCalls.filter((call, index) => {
      const after = caseCalls.slice(index + 1);
      call.recovered =
        call.code === 1_004_003 &&
        after.some(
          (next) =>
            next.url === '/admin-api/system/auth/refresh-token' &&
            next.code === 0,
        ) &&
        after.some(
          (next) =>
            next.url === call.url &&
            next.method === call.method &&
            next.code === 0,
        );
      return (
        !call.recovered &&
        (call.readError ||
          call.http >= 400 ||
          (typeof call.code === 'number' && call.code !== 0)) &&
        !allowedCodes.includes(call.code)
      );
    });
    assert.equal(failures.length, 0, JSON.stringify(failures));
    assert.equal(
      errors.length,
      firstError,
      JSON.stringify(errors.slice(firstError)),
    );
  } catch (error) {
    entry.status = 'failed';
    entry.error = error.message.replaceAll(
      /Bearer\s+[^\s]+/gi,
      'Bearer [redacted]',
    );
    const file = `${String(results.length + 1).padStart(3, '0')}-failure`;
    if (page.isClosed()) {
      entry.browserClosed = true;
    } else {
      await page.screenshot({ path: join(output, `${file}.png`) });
      await writeFile(
        join(output, `${file}.txt`),
        await page.locator('body').ariaSnapshot(),
      );
      entry.evidence = `${evidencePhase}/${file}`;
    }
  }
  await Promise.all(pending);
  entry.elapsedMs = Date.now() - started;
  entry.requests = calls.slice(firstCall);
  entry.pageErrors = errors.slice(firstError);
  results.push(entry);
  await writeFile(
    join(output, 'results.json'),
    JSON.stringify(results, null, 2),
  );
  process.stdout.write(
    `${JSON.stringify({
      name,
      status: entry.status,
      error: entry.error,
      requests: entry.requests.length,
    })}\n`,
  );
  assert.ok(!page.isClosed(), '浏览器已关闭，本阶段停止，保留失败证据');
  if (entry.status === 'failed') {
    currentCase = `${name}:cleanup`;
    await page.goto(`${server.origin}/#/dashboard/analytics`, {
      waitUntil: 'domcontentloaded',
    });
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.locator('#__vben_main_content').waitFor({ timeout: 20_000 });
    await settle();
  }
  return entry;
}

const api = {
  page,
  context,
  server,
  work,
  output,
  test,
  assert,
  settle,
  async binary(path, destination) {
    requestSource = 'browser-api';
    try {
      const result = await page.evaluate(
        async ({ path, authorization }) => {
          const response = await fetch(path, {
            headers: { Authorization: authorization },
          });
          return {
            http: response.status,
            contentType: response.headers.get('content-type'),
            bytes: [...new Uint8Array(await response.arrayBuffer())],
          };
        },
        { path, authorization },
      );
      await writeFile(destination, Buffer.from(result.bytes));
      return {
        http: result.http,
        contentType: result.contentType,
        bytes: result.bytes.length,
      };
    } finally {
      requestSource = 'ui';
    }
  },
  async upload(path, file, fields = {}) {
    const content = (await readFile(file)).toString('base64');
    requestSource = 'browser-api';
    try {
      return await page.evaluate(
        async ({ path, content, name, fields, authorization }) => {
          const form = new FormData();
          form.append(
            'file',
            new File(
              [Uint8Array.from(atob(content), (value) => value.codePointAt(0))],
              name,
            ),
          );
          for (const [key, value] of Object.entries(fields))
            form.append(key, String(value));
          const response = await fetch(path, {
            method: 'POST',
            headers: { Authorization: authorization },
            body: form,
          });
          return { http: response.status, body: await response.json() };
        },
        { path, content, name: basename(file), fields, authorization },
      );
    } finally {
      requestSource = 'ui';
    }
  },
  async request(
    path,
    {
      method = 'GET',
      data,
      auth = true,
      credentials = 'same-origin',
      headers = {},
      form,
    } = {},
  ) {
    requestSource = 'browser-api';
    try {
      return await page.evaluate(
        async ({
          path,
          method,
          data,
          authorization,
          credentials,
          headers,
          form,
        }) => {
          const options = {
            method,
            credentials,
            headers: {
              ...(authorization ? { Authorization: authorization } : {}),
              ...(data === undefined
                ? {}
                : { 'Content-Type': 'application/json' }),
              ...headers,
            },
          };
          if (form) options.body = new URLSearchParams(form);
          else if (data !== undefined) options.body = JSON.stringify(data);
          const response = await fetch(path, options);
          return { http: response.status, body: await response.json() };
        },
        {
          path,
          method,
          data,
          authorization: auth ? authorization : undefined,
          credentials,
          headers,
          form,
        },
      );
    } finally {
      requestSource = 'ui';
    }
  },
  async goto(path) {
    await page.goto(`${server.origin}/#${path}`, {
      waitUntil: 'domcontentloaded',
    });
    await page.locator('#__vben_main_content').waitFor({ timeout: 20_000 });
    await page.waitForFunction(
      (expected) =>
        document.querySelector('#app')?.__vue_app__?.config.globalProperties
          .$router.currentRoute.value.path === expected,
      path,
    );
    await page.waitForFunction(
      () =>
        !document.querySelector(
          '#__vben_main_content [class*="-enter-active"], #__vben_main_content [class*="-leave-active"]',
        ),
    );
    await page.waitForTimeout(200);
    await settle();
  },
  async login(username = 'admin', password = 'admin123') {
    await page.goto(`${server.origin}/#/auth/login`);
    await page.waitForFunction(
      () =>
        document.querySelector('#__vben_main_content') ||
        document.querySelector('input[placeholder="请输入用户名"]'),
    );
    if (!page.url().includes('#/auth/')) return;
    await page.getByRole('textbox', { name: '请输入用户名' }).fill(username);
    if (await page.getByRole('combobox').count()) {
      await page.getByRole('combobox').first().press('Enter');
      await page.getByRole('option', { name: '渡山无界', exact: true }).click();
    }
    await page.getByPlaceholder('密码', { exact: true }).fill(password);
    await page.getByRole('button', { name: 'login', exact: true }).click();
    await page.waitForURL(
      (url) => url.hash.startsWith('#/') && !url.hash.startsWith('#/auth/'),
      {
        timeout: 20_000,
      },
    );
    await settle();
  },
};
try {
  const run = (
    await import(
      pathToFileURL(
        join(dirname(fileURLToPath(import.meta.url)), `${phase}.mjs`),
      ).href
    )
  ).default;
  await run(api);
} finally {
  await Promise.all(pending);
  await writeFile(join(output, 'calls.json'), JSON.stringify(calls, null, 2));
  await writeFile(
    join(output, 'page-errors.json'),
    JSON.stringify(errors, null, 2),
  );
  await appendFile(
    join(work, 'browser/phases.ndjson'),
    `${JSON.stringify({
      phase: evidencePhase,
      at: new Date().toISOString(),
      passed: results.filter((r) => r.status === 'passed').length,
      failed: results.filter((r) => r.status === 'failed').length,
    })}\n`,
  );
  if (results.some((result) => result.status === 'failed'))
    process.exitCode = 1;
  await context.close();
}
