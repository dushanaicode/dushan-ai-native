import type { App, InjectionKey } from 'vue';

import type { DictionaryRuntime } from './runtime';

import { inject } from 'vue';

export const dictionaryKey: InjectionKey<DictionaryRuntime> =
  Symbol('dictionary');

export function provideDictionary(app: App, dictionary: DictionaryRuntime) {
  app.provide(dictionaryKey, dictionary);
  app.onUnmount(() => dictionary.dispose());
}

export function useDictionary() {
  const dictionary = inject(dictionaryKey);
  if (!dictionary) throw new Error('使用字典组件前必须提供 DictionaryRuntime');
  return dictionary;
}
