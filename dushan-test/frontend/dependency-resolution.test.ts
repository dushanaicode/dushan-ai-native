// @vitest-environment node

import { execFile } from 'node:child_process';
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

import { afterAll, beforeAll, describe, expect, it } from 'vitest';

const frontend = fileURLToPath(
  new URL('../../dushan-admin-frontend/', import.meta.url),
);
const require = createRequire(resolve(frontend, 'package.json'));
const execute = promisify(execFile);
let temporary: string;

beforeAll(async () => {
  const parent = resolve(frontend, 'Temp/frontend-foundation');
  await mkdir(parent, { recursive: true });
  temporary = await mkdtemp(resolve(parent, 'dependency resolution '));
});

afterAll(async () => {
  await rm(temporary, { force: true, recursive: true });
});

async function run(bin: string, args: string[], cwd = frontend) {
  try {
    const result = await execute(process.execPath, [bin, ...args], {
      cwd,
      env: {
        ...process.env,
        TEMP: temporary,
        TMP: temporary,
        TMPDIR: temporary,
      },
      timeout: 30_000,
      maxBuffer: 2 * 1024 * 1024,
    });
    return { code: 0, output: result.stdout + result.stderr };
  } catch (error) {
    const failure = error as Error & {
      code?: number | string;
      stdout?: string;
      stderr?: string;
    };
    if (typeof failure.code !== 'number') throw error;
    return {
      code: failure.code,
      output: (failure.stdout ?? '') + (failure.stderr ?? ''),
    };
  }
}

describe('配置依赖的实际解析与规则执行', () => {
  it('从父仓运行 Oxlint 时能加载配置包插件，并实际执行插件规则', async () => {
    const bin = resolve(
      dirname(require.resolve('oxlint/package.json')),
      'bin/oxlint',
    );
    const file = resolve(temporary, 'plugin-fixture.tsx');
    const args = [
      '--config',
      resolve(frontend, 'oxlint.config.ts'),
      '--no-ignore',
      '--threads=2',
      file,
    ];
    await writeFile(file, 'export const value = 1;\n');
    const valid = await run(bin, args, dirname(frontend));
    expect(valid.code).toBe(0);
    expect(valid.output).not.toContain('Disabling rule');
    await writeFile(
      file,
      '/* eslint-enable no-console */\nexport const value = 1;\n',
    );
    const invalid = await run(bin, args, dirname(frontend));
    expect(invalid.code).toBe(1);
    expect(invalid.output).toContain('no-unused-enable');
    await writeFile(file, 'export const demo = <div className="p-2 p-4" />;\n');
    const conflicting = await run(bin, args, dirname(frontend));
    expect(conflicting.code).toBe(1);
    expect(conflicting.output).toContain('no-conflicting-classes');
  });

  it('通过 Stylelint 解析 Vue/SCSS，并对实际样式错误返回失败', async () => {
    const bin = resolve(
      dirname(require.resolve('stylelint/package.json')),
      'bin/stylelint.mjs',
    );
    const vue = resolve(temporary, 'fixture.vue');
    const scss = resolve(temporary, 'fixture.scss');
    const ignore = resolve(temporary, 'empty-ignore');
    await writeFile(ignore, '');
    await writeFile(
      vue,
      '<template><div class="fixture" /></template>\n<style>\n.fixture {\n  color: #fff;\n}\n</style>\n',
    );
    await writeFile(
      scss,
      '$accent: #fff;\n\n.fixture {\n  color: $accent;\n}\n',
    );
    const args = [
      '--config',
      resolve(frontend, 'stylelint.config.mjs'),
      '--ignore-path',
      ignore,
      vue,
      scss,
    ];
    const valid = await run(bin, args);
    expect(valid).toEqual({ code: 0, output: '' });
    await writeFile(scss, '.fixture { colorr: #fff; }\n');
    const invalid = await run(bin, args);
    expect(invalid.code).toBe(2);
    expect(invalid.output).toContain('property-no-unknown');
  });

  it('通过 Commitlint 继承共享规则和自定义 scope，合法和非法提交消息有不同结果', async () => {
    const bin = resolve(
      dirname(require.resolve('@commitlint/cli/package.json')),
      'cli.js',
    );
    const file = resolve(temporary, 'commit-message');
    const args = [
      '--config',
      resolve(frontend, '.commitlintrc.js'),
      '--edit',
      file,
    ];
    await writeFile(file, 'feat(project): 验证前端基础能力\n');
    const valid = await run(bin, args);
    expect(valid.code).toBe(0);
    await writeFile(file, 'feat(nonexistent-scope): 验证前端基础能力\n');
    const invalid = await run(bin, args);
    expect(invalid.code).toBe(1);
    expect(invalid.output).toContain('scope must be one of');
  });
});
