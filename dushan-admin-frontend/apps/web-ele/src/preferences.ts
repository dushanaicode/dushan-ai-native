import { defineOverridesPreferences } from '@vben/preferences';

import { projectLinks } from '#/services/doc-links';

export const applicationAccessMode = 'mixed';

/**
 * @description 项目配置文件
 * 只需要覆盖项目中的一部分配置，不需要的配置不用覆盖，会自动使用默认配置
 * !!! 更改配置后请清空缓存，否则可能不生效
 */
export const overridesPreferences = defineOverridesPreferences({
  // overrides
  app: {
    // 后端菜单（System/Infra）与本地路由（dashboard/profile/demos）合并：
    // 后端菜单种子没有首页节点，纯 backend 模式会让 defaultHomePath 落到 404。
    accessMode: applicationAccessMode,
    name: import.meta.env.VITE_APP_TITLE,
  },
  copyright: {
    companyName: 'dushan-ai-native',
    companySiteLink: projectLinks.github,
    date: '2026',
    enable: true,
    icp: '',
    icpLink: '',
  },
  // 暂无品牌 Logo 图片，只显示应用名文字
  logo: {
    source: '',
    sourceDark: '',
  },
});
