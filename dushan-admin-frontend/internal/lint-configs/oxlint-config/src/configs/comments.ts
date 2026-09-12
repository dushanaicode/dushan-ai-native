import type { OxlintConfig } from 'oxlint';

import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);

const comments: OxlintConfig = {
  jsPlugins: [
    {
      name: 'eslint-comments',
      specifier:
        require.resolve('@eslint-community/eslint-plugin-eslint-comments'),
    },
  ],
  rules: {
    'eslint/no-underscore-dangle': 'off',
    'eslint-comments/no-aggregating-enable': 'error',
    'eslint-comments/no-duplicate-disable': 'error',
    'eslint-comments/no-unlimited-disable': 'error',
    'eslint-comments/no-unused-enable': 'error',
  },
};

export { comments };
