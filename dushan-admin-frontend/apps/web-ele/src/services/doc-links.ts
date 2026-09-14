/** 页面文档条目：guidePath 指向免费文档，deepDivePath 指向星球源码解读跳转页。 */
export interface DocEntry {
  title: string;
  guidePath: string;
  deepDivePath?: string;
}

export type DocChannel = 'doc_alert' | 'help_menu' | 'login';

export interface DocLinkConfig {
  alertEnabled: boolean;
  docSite?: URL;
  deepDiveSite?: URL;
}

/**
 * 页面文档登记表，只登记文档站已经发布的条目。
 *
 * 页面使用 `<DocAlert :entry="docEntries.xxx" />`，路径相对站点根且不以 / 开头。
 */
export const docEntries = {} satisfies Record<string, DocEntry>;

export const projectLinks = {
  github: 'https://github.com/dushanaicode/dushan-ai-native',
  // 国内镜像仓库
  mirror: 'https://gitee.com/dushan-ai/dushan-ai-native',
  issues: 'https://github.com/dushanaicode/dushan-ai-native/issues',
} as const;

function readSite(name: string, value: string) {
  if (value === '') return undefined;
  const url = new URL(value);
  if (
    !['http:', 'https:'].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash
  )
    throw new TypeError(`${name} 必须是不含凭据、查询和片段的 HTTP(S) 地址`);
  if (!url.pathname.endsWith('/')) url.pathname = `${url.pathname}/`;
  return url;
}

export function readDocLinkConfig(environment: {
  alertEnabled: string;
  docSiteUrl: string;
  deepDiveSiteUrl: string;
}): DocLinkConfig {
  if (!['false', 'true'].includes(environment.alertEnabled))
    throw new TypeError('VITE_DOC_ALERT_ENABLED 必须是 true 或 false');
  return {
    alertEnabled: environment.alertEnabled === 'true',
    docSite: readSite('VITE_DOC_SITE_URL', environment.docSiteUrl),
    deepDiveSite: readSite(
      'VITE_DEEP_DIVE_SITE_URL',
      environment.deepDiveSiteUrl,
    ),
  };
}

export function useDocLinkConfig() {
  return readDocLinkConfig({
    alertEnabled: import.meta.env.VITE_DOC_ALERT_ENABLED,
    docSiteUrl: import.meta.env.VITE_DOC_SITE_URL,
    deepDiveSiteUrl: import.meta.env.VITE_DEEP_DIVE_SITE_URL,
  });
}

/** 拼接站内地址并附加 UTM；content 只写文档路径或入口名，不含用户和租户信息。 */
export function buildDocUrl(
  site: URL,
  path: string,
  tracking: { channel: DocChannel; content: string },
) {
  if (path.startsWith('/') || path.includes('..') || path.includes(':'))
    throw new TypeError('文档路径必须是站点内相对路径');
  const url = new URL(path, site);
  url.searchParams.set('utm_source', 'dushan-ai-native');
  url.searchParams.set('utm_medium', 'admin');
  url.searchParams.set('utm_campaign', tracking.channel);
  url.searchParams.set('utm_content', tracking.content);
  return url.href;
}
