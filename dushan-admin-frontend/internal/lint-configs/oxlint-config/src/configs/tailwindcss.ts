import type { OxlintConfig } from 'oxlint';

import { createRequire } from 'node:module';
import { dirname } from 'node:path';

import eslintPluginBetterTailwindcss from 'eslint-plugin-better-tailwindcss';
import { getDefaultSelectors } from 'eslint-plugin-better-tailwindcss/defaults';
import { SelectorKind } from 'eslint-plugin-better-tailwindcss/types';

const require = createRequire(import.meta.url);

const selectors = [
  ...getDefaultSelectors(),
  {
    kind: SelectorKind.Attribute,
    match: [{ type: 'objectValues' }],
    name: '^classNames$',
  },
];

const entryPoint = require.resolve('@vben/tailwind-config/theme');

const settings = {
  cwd: dirname(entryPoint),
  entryPoint,
  selectors,
};

const tailwindcss: OxlintConfig = {
  // Generated shadcn-ui internals are intentionally left unmanaged.
  ignorePatterns: ['packages/@core/ui-kit/shadcn-ui/**/*'],
  jsPlugins: [
    {
      name: 'better-tailwindcss',
      specifier: require.resolve('eslint-plugin-better-tailwindcss'),
    },
  ],
  rules: {
    ...eslintPluginBetterTailwindcss.configs.recommended.rules,
    'better-tailwindcss/enforce-consistent-class-order': [
      'error',
      {
        detectComponentClasses: true,
        unknownClassOrder: 'asc',
        unknownClassPosition: 'start',
      },
    ],
    // Let Prettier own wrapping decisions to avoid ping-pong formatting.
    'better-tailwindcss/enforce-consistent-line-wrapping': 'off',
    'better-tailwindcss/no-unknown-classes': 'off',
  },
  settings: {
    'better-tailwindcss': settings,
    'eslint-plugin-better-tailwindcss': settings,
  },
};

export { tailwindcss };
