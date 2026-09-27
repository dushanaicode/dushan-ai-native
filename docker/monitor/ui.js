function UIConfig() {
  const theme = new URLSearchParams(window.location.search).get('nativeTheme');
  if (theme === 'dark' || theme === 'light') {
    // 在Jaeger自身启动时设置其主题偏好，保留完整搜索、导航及详情界面。
    // key对应固定的Jaeger 2.21 UI；升级时验证其主题存储契约。
    try {
      window.localStorage.setItem('jaeger-ui-theme', JSON.stringify(theme));
    } catch (error) {
      console.warn('Jaeger主题偏好无法保存：', error);
    }
  }
  return { themes: { enabled: true }, archiveEnabled: false };
}
