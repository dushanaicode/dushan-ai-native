import { fileURLToPath } from 'node:url';

import { defineConfig, defineRuntimeBoundaries } from '@vben/eslint-config';

const root = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig([defineRuntimeBoundaries(root)]);
