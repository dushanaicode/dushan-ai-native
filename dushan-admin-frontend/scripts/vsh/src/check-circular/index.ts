import type { CAC } from 'cac';

import { extname, resolve } from 'node:path';

import { getStagedFiles } from '@vben/node-utils';

import { circularDepsDetect } from 'circular-dependency-scanner';

import { CheckError } from '../check-error';

const DEFAULT_CONFIG = {
  includeTypes: false,
  allowedExtensions: [
    '.cjs',
    '.cts',
    '.js',
    '.jsx',
    '.mjs',
    '.mts',
    '.ts',
    '.tsx',
    '.vue',
  ],
  ignoreDirs: [
    '.git',
    'node_modules',
    'dist',
    'Temp',
    '.turbo',
    'output',
    '.cache',
  ],
  threshold: 0,
};

interface CheckCircularConfig {
  includeTypes?: boolean;
  allowedExtensions?: string[];
  ignoreDirs?: string[];
  threshold?: number;
}

interface CommandOptions {
  config?: CheckCircularConfig;
  staged: boolean;
  verbose: boolean;
}

/** 按实际参与本次检查的循环数量判定，不缓存跨调用的扫描结果。 */
async function checkCircular({ config = {}, staged, verbose }: CommandOptions) {
  const { allowedExtensions, ignoreDirs, includeTypes, threshold } = {
    ...DEFAULT_CONFIG,
    ...config,
  };
  if (!Number.isSafeInteger(threshold) || threshold < 0) {
    throw new CheckError(
      'Circular dependency threshold must be a non-negative integer.',
    );
  }

  const cwd = process.cwd();
  const stagedPaths = staged ? await getStagedFiles() : undefined;
  const stagedFiles = stagedPaths
    ? new Set(
        stagedPaths.filter((file) => allowedExtensions.includes(extname(file))),
      )
    : undefined;

  // 公开 API 对无循环直接返回 []，不再依赖 CLI 是否生成结果文件。
  // scanner 的 Windows absolute 模式混用路径分隔符；本层统一转换暂存路径。
  const cycles = await circularDepsDetect({
    absolute: false,
    cwd,
    excludeTypes: !includeTypes,
    ignore: ignoreDirs.map(
      (directory) =>
        `**/${directory.replaceAll('\\', '/').replace(/\/+$/, '')}/**`,
    ),
  });
  const selected = stagedFiles
    ? cycles.filter((cycle) =>
        cycle.some((file) => stagedFiles.has(resolve(cwd, file))),
      )
    : cycles;

  if (verbose) {
    for (const [index, cycle] of selected.entries()) {
      console.log(`\nCircular dependency #${index + 1}:`);
      for (const file of cycle) console.log(`  → ${file}`);
    }
    console.log(
      `Circular dependencies (${includeTypes ? 'all imports' : 'runtime'}): ${selected.length}; threshold: ${threshold}`,
    );
  }
  if (selected.length > threshold) {
    throw new CheckError(
      `Found ${selected.length} circular dependencies; allowed threshold is ${threshold}.`,
    );
  }
}

function defineCheckCircularCommand(cac: CAC): void {
  cac
    .command('check-circular')
    .option(
      '--include-types',
      'Include type-only imports in the dependency graph',
    )
    .option('--staged', 'Only check cycles involving staged files')
    .option('--verbose', 'Show detailed information')
    .option('--threshold <number>', 'Maximum allowed circular dependencies', {
      default: 0,
    })
    .option('--ignore-dirs <dirs>', 'Directories to ignore, comma separated')
    .usage('Analyze project circular dependencies')
    .action(
      async ({ ignoreDirs, includeTypes, staged, threshold, verbose }) => {
        await checkCircular({
          config: {
            includeTypes: includeTypes ?? false,
            threshold: Number(threshold),
            ...(ignoreDirs && {
              ignoreDirs: String(ignoreDirs)
                .split(',')
                .map((value) => value.trim())
                .filter(Boolean),
            }),
          },
          staged: staged ?? false,
          verbose: verbose ?? true,
        });
      },
    );
}

export { type CheckCircularConfig, defineCheckCircularCommand };
