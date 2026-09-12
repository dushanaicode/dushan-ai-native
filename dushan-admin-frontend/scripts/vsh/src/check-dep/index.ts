import type { CAC } from 'cac';

import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';

import { execa } from '@vben/node-utils';

import { CheckError } from '../check-error';

const require = createRequire(import.meta.url);
const knipCli = join(dirname(require.resolve('knip')), '..', 'bin', 'knip.js');

/** 保留 Knip 原生诊断，发现依赖问题和工具故障都不能作为成功返回。 */
async function runKnipCheck(): Promise<void> {
  const cwd = process.cwd();
  const result = await execa(
    process.execPath,
    [
      knipCli,
      '--include',
      'dependencies,unlisted,unresolved,binaries',
      '--no-config-hints',
    ],
    { cwd, reject: false, stdio: 'inherit' },
  );
  if (result.failed) {
    throw new CheckError(
      `Dependency check failed (exit code ${result.exitCode ?? 'unknown'}).`,
    );
  }
  console.log('Dependency check completed, no issues found.');
}

function defineCheckDepCommand(cac: CAC): void {
  cac
    .command('check-dep')
    .usage('Analyze project dependencies using knip')
    .action(runKnipCheck);
}

export { defineCheckDepCommand };
