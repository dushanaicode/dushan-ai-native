# Native 浏览器测试记录脚本

这组脚本用于 2026-09-25 的完整应用验证和缺陷复现，不是已全部通过的一键 CI 套件。测试结论和已知前置见项目 `.docs/reports/2026-09-25-frontend-full-check.md`。

- `run.mjs` 使用真实 Chrome/Edge 页面，记录请求、业务码、截图和断言结果。
- 各阶段依赖前一阶段创建的隔离数据；`*-state.json` 仅在 `Temp/` 下生成。
- `accounts`、`content-crud`、`infra-crud`、`admin-crud` 创建操作数据；后续删除阶段会删除这些测试数据。
- `auth-matrix` 只验证未登录拒绝，不代表正向业务通过。
- `oauth-probes` 等补充接口由浏览器 fetch 发起，记录为 `browser-api`。
- `session_ttl.py` 调整寿命前验证隔离 MySQL datadir 和 Redis dir，必须执行 restore。
- `module_infra/test_frontend_browser_audit.py` 是显式启用的测试宿主：默认跳过，使用独立数据库/Redis、本地 SMTP、模拟短信，禁止外部邮件投递。

执行前必须提供本轮独立资源清单。不要把 `server.json` 或资源清单指向真实业务环境。所有 TEMP/TMP/TMPDIR、浏览器 profile、下载、缓存均需指向命令工作目录的 `Temp/`。

阶段运行示例（从 Native 根目录，服务已就绪）：

```powershell
$task = (Resolve-Path 'Temp/frontend-full-check').Path
$env:TEMP = $task
$env:TMP = $task
$env:TMPDIR = $task
$env:NODE_COMPILE_CACHE = Join-Path $task 'node-cache'
$env:JITI_FS_CACHE = '0'
$env:DUSHAN_AUDIT_WORKDIR = $task
# PLAYWRIGHT_ENTRY 指向已有 Playwright 的 index.mjs，不安装全局依赖。
node dushan-test/tools/frontend-audit/run.mjs inventory
```

第三个参数是证据阶段名，可保留复测前的原始记录；`DUSHAN_AUDIT_CASE_FILTER` 用于只执行匹配的用例。过滤时仍须满足数据和登录前置，不得把前置未执行的结果当成业务通过。

代码检查使用项目 ESLint/Oxfmt 与 OxLint 配置。浏览器断言保留紧凑的 `(await request()).field` 写法，OxLint 仅放宽 `unicorn/no-await-expression-member` 风格规则；其余规则、Node 语法检查和 Python Ruff 保持启用。没有改变产品 lint 配置。
