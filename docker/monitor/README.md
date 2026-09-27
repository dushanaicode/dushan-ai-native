# Native 本地链路追踪

使用官方Jaeger **2.21.0**镜像，Compose固定其摘要，独立容器`dushan-native-jaeger`。界面`http://localhost:16686`，OTLP gRPC接收地址`http://127.0.0.1:4317`，仅绑定本机。追踪数据位于仓库`Temp/monitor-runtime/jaeger-data`，保留72小时；容器临时目录绑定`Temp/monitor-runtime/jaeger`。运行期间保留这些目录。

`jaeger.yaml`配置OTLP接收、批处理、Badger存储与查询；`ui.js`通过Jaeger支持的`UIConfig()`入口开启完整明暗主题。Native监控页以`nativeTheme=dark|light`传递当前主题，Jaeger在自身启动时写入主题偏好；系统切换主题后重新加载iframe，查询条件会重置。未带该参数的独立窗口仍使用Jaeger自身的主题偏好。`jaeger-ui-theme`为固定版本的存储键，升级时须复验。

此处保留完整查询界面，不使用会隐藏搜索表单和导航的`uiEmbed=v0`模式。

在Native仓库根目录创建上述临时目录后，使用WSL Docker运行：

```powershell
$monitorTemp = Join-Path (Get-Location).Path 'Temp\monitor-runtime'
New-Item -ItemType Directory -Path "$monitorTemp\jaeger", "$monitorTemp\jaeger-data", "$monitorTemp\docker-cli" -Force | Out-Null
$env:TEMP = $monitorTemp
$env:TMP = $monitorTemp
$env:TMPDIR = $monitorTemp
$linuxTemp = '/mnt/e/dushan/dushan-ai-native/Temp/monitor-runtime'
$dockerArgs = @('-d', 'Ubuntu-24.04', '-u', 'root', '--cd', '/mnt/e/dushan/dushan-ai-native', '--exec', 'env', "TMPDIR=$linuxTemp", "TEMP=$linuxTemp", "TMP=$linuxTemp", 'docker', '--config', "$linuxTemp/docker-cli")
# 首次运行须显式拉取Compose所固定的官方镜像。
wsl @dockerArgs pull quay.io/jaegertracing/jaeger@sha256:3d0ac795ff98aa04d1be04311d2dac6c25b4bfc8322dc02e53bc5b170c5018c3
wsl @dockerArgs compose -f docker/monitor/compose.yaml config --quiet
wsl @dockerArgs compose -f docker/monitor/compose.yaml up -d --pull never
```

后端`application-local.yaml`中的`config.models.monitor`须启用，并配置`exporter: otlp`、`endpoint: http://127.0.0.1:4317`。修改后重启后端。停止容器不删除运行数据目录。此配置用于本地开发；远程部署应使用部署环境的地址和访问控制。

升级前应停止当前Jaeger后备份数据目录和Compose配置。此次1.76→2.21已保留原Badger数据并验证历史追踪可读、新HTTP/SQL追踪可接收。新版服务列表使用`/api/v3/services`，不要用已移除的`/api/services`判断运行状态。

配置依据：[Jaeger UI配置](https://www.jaegertracing.io/docs/2.21/deployment/frontend-ui/)、[Badger存储](https://www.jaegertracing.io/docs/2.21/storage/badger/)。
