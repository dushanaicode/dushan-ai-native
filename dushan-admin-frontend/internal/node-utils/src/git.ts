import path from 'node:path';

import { execa } from 'execa';

export * from '@changesets/git';

/**
 * 返回当前工作区范围内的暂存文件绝对路径，支持前端嵌套在父 Git 仓库中。
 */
async function getStagedFiles(cwd = process.cwd()): Promise<string[]> {
  const { stdout } = await execa(
    'git',
    [
      '-c',
      'submodule.recurse=false',
      'diff',
      '--staged',
      '--diff-filter=ACMR',
      '--name-only',
      '--ignore-submodules',
      '--relative',
      '-z',
      '--',
      '.',
    ],
    { cwd },
  );

  return [
    ...new Set(
      stdout
        .split('\u0000')
        .filter(Boolean)
        .map((file) => path.resolve(cwd, file)),
    ),
  ];
}

export { getStagedFiles };
