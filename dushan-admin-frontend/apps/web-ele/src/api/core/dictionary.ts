import { requestClient } from '#/api/request';

/**
 * 获取当前身份可见的全部启用字典数据
 *
 * 返回值交由 DictionaryRuntime 的 schema 校验，这里不预先解析结构。
 */
export async function getDictionaryDataApi(signal: AbortSignal) {
  return requestClient.get<unknown>('/system/dict/data/simple-list', {
    signal,
  });
}
