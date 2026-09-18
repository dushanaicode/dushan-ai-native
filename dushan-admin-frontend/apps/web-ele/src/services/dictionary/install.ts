import type { App } from 'vue';

import type { SessionCoordinator } from '../session/coordinator';

import { computed } from 'vue';

import { preferences } from '@vben/preferences';

import { getDictionaryDataApi } from '../../api/core/dictionary';
import { provideDictionary } from './context';
import { DictionaryRuntime } from './runtime';

/**
 * 装配字典运行时。
 *
 * 与 context.ts 分开，使 dict-tag 等组件只依赖注入入口，不牵入请求栈。
 * 标签语言由请求层的 Accept-Language 头决定，这里只在偏好语言变化时让缓存失效。
 */
export function installDictionary(app: App, session: SessionCoordinator) {
  const dictionary = new DictionaryRuntime({
    loader: getDictionaryDataApi,
    locale: computed(() => preferences.app.locale),
    session,
  });
  provideDictionary(app, dictionary);
  return dictionary;
}
