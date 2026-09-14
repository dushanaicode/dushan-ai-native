// cspell:ignore umami
export type AnalyticsConfig =
  | { enabled: false }
  | { enabled: true; domains: string[]; scriptUrl: URL; websiteId: string };

const websiteIdPattern =
  /^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$/;
const domainPattern =
  /^[\da-z]([\da-z-]*[\da-z])?(\.[\da-z]([\da-z-]*[\da-z])?)+$/;

/**
 * 读取 Umami 统计配置：三项全部留空时关闭，开源部署默认不上报任何数据。
 *
 * 开启时必须限定上报域名，避免复制配置的其他部署被统计。
 */
export function readAnalyticsConfig(environment: {
  domains: string;
  scriptUrl: string;
  websiteId: string;
}): AnalyticsConfig {
  const values = [
    environment.scriptUrl,
    environment.websiteId,
    environment.domains,
  ];
  if (values.every((value) => value === '')) return { enabled: false };
  if (values.includes(''))
    throw new TypeError(
      'VITE_UMAMI_SCRIPT_URL、VITE_UMAMI_WEBSITE_ID、VITE_UMAMI_DOMAINS 必须同时配置或同时留空',
    );
  const scriptUrl = new URL(environment.scriptUrl);
  if (
    scriptUrl.protocol !== 'https:' ||
    scriptUrl.username ||
    scriptUrl.password ||
    scriptUrl.hash
  )
    throw new TypeError('VITE_UMAMI_SCRIPT_URL 必须是不含凭据的 HTTPS 地址');
  if (!websiteIdPattern.test(environment.websiteId))
    throw new TypeError('VITE_UMAMI_WEBSITE_ID 必须是 Umami 站点 UUID');
  const domains = environment.domains.split(',').map((domain) => domain.trim());
  if (!domains.every((domain) => domainPattern.test(domain)))
    throw new TypeError('VITE_UMAMI_DOMAINS 必须是逗号分隔的小写域名');
  return {
    enabled: true,
    domains,
    scriptUrl,
    websiteId: environment.websiteId,
  };
}

export function useAnalyticsConfig() {
  return readAnalyticsConfig({
    domains: import.meta.env.VITE_UMAMI_DOMAINS,
    scriptUrl: import.meta.env.VITE_UMAMI_SCRIPT_URL,
    websiteId: import.meta.env.VITE_UMAMI_WEBSITE_ID,
  });
}

/** 注入统计脚本；只统计页面访问，不附带用户、租户或查询参数。 */
export function installAnalytics(config: AnalyticsConfig, target: Document) {
  if (!config.enabled) return;
  const script = target.createElement('script');
  script.defer = true;
  script.src = config.scriptUrl.href;
  script.dataset.websiteId = config.websiteId;
  script.dataset.domains = config.domains.join(',');
  script.dataset.doNotTrack = 'true';
  script.dataset.excludeSearch = 'true';
  target.head.append(script);
}
