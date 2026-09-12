import type { OxlintConfig } from 'oxlint';

import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);

const command: OxlintConfig = {
  jsPlugins: [
    {
      name: 'command',
      specifier: require.resolve('eslint-plugin-command'),
    },
  ],
  rules: {
    'command/command': 'error',
  },
};

export { command };
