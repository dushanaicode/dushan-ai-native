import type { Linter, Rule } from 'eslint';

import { builtinModules } from 'node:module';
import { dirname, isAbsolute, relative, resolve, sep } from 'node:path';

const nodeModules = new Set(builtinModules);
const applicationPackage =
  /^@vben\/(?:web-(?:antd|antdv-next|ele|naive|tdesign)|playground)(?:\/|$)/;
const toolingPackage =
  /^@vben\/(?:node-utils|turbo-run|vsh|tsconfig|[^/]+-config)(?:\/|$)/;

function isWithin(directory: string, target: string) {
  const path = relative(directory, target);
  return path !== '..' && !path.startsWith(`..${sep}`) && !isAbsolute(path);
}

/** 给公共包补充静态导入边界，保持已有 no-restricted-imports 分层规则独立生效。 */
function defineRuntimeBoundaries(root: string): Linter.Config {
  const workspace = resolve(root);
  const rule: Rule.RuleModule = {
    meta: {
      type: 'problem',
      schema: [],
      messages: {
        application: '公共包运行源码不能导入应用内部模块：{{specifier}}。',
        tooling:
          '浏览器运行源码不能导入 Node 内置模块或工程工具：{{specifier}}。',
        privateInstall:
          '请通过已声明依赖的公开入口导入，不能依赖 .pnpm 私有安装路径：{{specifier}}。',
      },
    },
    create(context) {
      const filename = context.filename;
      const path = relative(workspace, filename).replaceAll('\\', '/');
      const runtime =
        (path.includes('/src/') || path.endsWith('.d.ts')) &&
        !/(?:^|\/)(?:__tests__|tests)\//.test(path) &&
        !/\.(?:test|spec|benchmark)\./.test(path);

      function check(value: unknown, node: Rule.Node) {
        if (typeof value !== 'string') return;
        const specifier = value.replaceAll('\\', '/');
        let messageId: 'application' | 'privateInstall' | 'tooling' | undefined;
        if (/(?:^|\/)node_modules\/\.pnpm(?:\/|$)/.test(specifier)) {
          messageId = 'privateInstall';
        } else if (runtime) {
          if (
            /^(?:#|@)\//.test(specifier) ||
            applicationPackage.test(specifier)
          ) {
            messageId = 'application';
          } else if (
            specifier.startsWith('node:') ||
            nodeModules.has(specifier) ||
            toolingPackage.test(specifier)
          ) {
            messageId = 'tooling';
          } else if (specifier.startsWith('.') || isAbsolute(specifier)) {
            const target = resolve(dirname(filename), specifier);
            if (isWithin(resolve(workspace, 'apps'), target)) {
              messageId = 'application';
            } else if (
              isWithin(resolve(workspace, 'internal'), target) ||
              isWithin(resolve(workspace, 'scripts'), target)
            ) {
              messageId = 'tooling';
            }
          }
        }
        if (messageId) context.report({ node, messageId, data: { specifier } });
      }

      return {
        ImportDeclaration(node) {
          check(node.source.value, node);
        },
        ExportAllDeclaration(node) {
          check(node.source.value, node);
        },
        ExportNamedDeclaration(node) {
          check(node.source?.value, node);
        },
        ImportExpression(node) {
          if (node.source.type === 'Literal') check(node.source.value, node);
          else if (
            node.source.type === 'TemplateLiteral' &&
            node.source.expressions.length === 0
          ) {
            check(node.source.quasis[0]?.value.cooked, node);
          }
        },
        TSImportType(node: Rule.Node) {
          const source = (
            node as { source?: { type: string; value?: unknown } }
          ).source;
          if (source?.type === 'Literal') {
            check(source.value, node);
          }
        },
        CallExpression(node) {
          if (
            node.callee.type !== 'Identifier' ||
            node.callee.name !== 'require'
          )
            return;
          const source = node.arguments[0];
          if (source?.type === 'Literal') check(source.value, node);
        },
      };
    },
  };

  return {
    name: 'vben/runtime-boundaries',
    basePath: workspace,
    files: ['packages/**/*.{js,jsx,ts,tsx,vue,cjs,mjs,cts,mts}'],
    plugins: { 'vben-boundaries': { rules: { 'runtime-imports': rule } } },
    rules: { 'vben-boundaries/runtime-imports': 'error' },
  };
}

export { defineRuntimeBoundaries };
