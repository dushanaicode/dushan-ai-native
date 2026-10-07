param(
    [Parameter(Mandatory = $true)][ValidateSet('start', 'stop', 'status', 'run')][string]$Action,
    [string[]]$Paths = @('server', 'framework', 'module_system', 'module_infra'),
    [switch]$IncludeSmoke
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$run = Join-Path $repo 'Temp\test-resources'
$linuxRepo = '/mnt/' + $repo.Substring(0, 1).ToLower() + ($repo.Substring(2) -replace '\\', '/')
$linuxRun = $linuxRepo + '/Temp/test-resources'
$mysqlBin = 'C:\Program Files\MySQL\MySQL Server 8.4\bin'
$mysqlPort = 33170
$redisPort = 63870
$container = 'dushan-unattended-test-redis'
$database = 'native_test'
$manifest = Join-Path $run 'resources.json'
$keepalive = Join-Path $run 'wsl-keepalive.pid'
$env:TEMP = $run
$env:TMP = $run
$env:TMPDIR = $run
$dockerArgs = @('-d', 'Ubuntu-24.04', '-u', 'root', '--cd', $linuxRepo, '--exec', 'env', "TMPDIR=$linuxRun", "TEMP=$linuxRun", "TMP=$linuxRun", 'docker', '--config', "$linuxRun/docker-cli")

function Test-Port([int]$Port) {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $client.Connect('127.0.0.1', $Port)
        $true
    } catch [System.Net.Sockets.SocketException] {
        $false
    } finally {
        $client.Dispose()
    }
}

function Get-RedisState {
    $state = & wsl @dockerArgs ps --all --filter "name=^/$container$" --format '{{.State}}'
    if ($LASTEXITCODE -ne 0) { throw '无法查询 Docker 容器状态' }
    if ([string]::IsNullOrWhiteSpace($state)) { return 'absent' }
    $state.Trim()
}

function Start-Resources {
    foreach ($folder in @('mysql\data', 'mysql\tmp', 'mysql\files', 'redis', 'container-tmp', 'docker-cli', 'reports')) {
        New-Item -ItemType Directory -Path (Join-Path $run $folder) -Force | Out-Null
    }
    $alive = $null
    if (Test-Path $keepalive) { $alive = Get-Process -Id ([int](Get-Content $keepalive)) -ErrorAction SilentlyContinue }
    if (-not $alive) {
        # WSL 空闲时会关闭 dockerd，测试期间用一个常驻进程保持 WSL 运行。
        $proc = Start-Process -FilePath 'wsl.exe' -ArgumentList @('-d', 'Ubuntu-24.04', '--exec', 'sleep', 'infinity') -WindowStyle Hidden -PassThru
        Set-Content -LiteralPath $keepalive -Value $proc.Id -Encoding ascii
    }
    & wsl -d Ubuntu-24.04 -u root --exec systemctl is-active docker | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'WSL 中的 Docker 未运行' }

    $datadir = Join-Path $run 'mysql\data'
    $mysqlArgs = @('--no-defaults', ('--datadir="' + $datadir + '"'), ('--tmpdir="' + (Join-Path $run 'mysql\tmp') + '"'), '--skip-log-bin', '--mysqlx=0')
    if (-not (Test-Port $mysqlPort)) {
        if (-not (Test-Path (Join-Path $datadir 'mysql'))) {
            $init = Start-Process -FilePath (Join-Path $mysqlBin 'mysqld.exe') -ArgumentList ($mysqlArgs + '--initialize-insecure') -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput (Join-Path $run 'mysql\initialize.stdout.log') -RedirectStandardError (Join-Path $run 'mysql\initialize.stderr.log')
            if ($init.ExitCode -ne 0) { throw 'MySQL 初始化失败' }
        }
        $serverArgs = $mysqlArgs + @('--bind-address=127.0.0.1', "--port=$mysqlPort", '--innodb-buffer-pool-size=256M', '--max-connections=500', ('--secure-file-priv="' + (Join-Path $run 'mysql\files') + '"'), ('--log-error="' + (Join-Path $run 'mysql\mysql.log') + '"'))
        Start-Process -FilePath (Join-Path $mysqlBin 'mysqld.exe') -ArgumentList $serverArgs -WindowStyle Hidden -RedirectStandardOutput (Join-Path $run 'mysql\server.stdout.log') -RedirectStandardError (Join-Path $run 'mysql\server.stderr.log') | Out-Null
        foreach ($i in 1..60) {
            & (Join-Path $mysqlBin 'mysqladmin.exe') --host=127.0.0.1 --port=$mysqlPort --user=root --connect-timeout=2 ping 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) { break }
            Start-Sleep -Milliseconds 500
        }
    }
    $actual = (& (Join-Path $mysqlBin 'mysql.exe') --host=127.0.0.1 --port=$mysqlPort --user=root -N -e 'SELECT @@datadir').Trim()
    if ($LASTEXITCODE -ne 0 -or [IO.Path]::GetFullPath($actual).TrimEnd('\') -ne [IO.Path]::GetFullPath($datadir).TrimEnd('\')) {
        throw "端口 $mysqlPort 上不是本测试库的 MySQL"
    }
    & (Join-Path $mysqlBin 'mysql.exe') --host=127.0.0.1 --port=$mysqlPort --user=root -e "CREATE DATABASE IF NOT EXISTS $database CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    if ($LASTEXITCODE -ne 0) { throw '测试数据库创建失败' }

    $state = Get-RedisState
    if ($state -ne 'running') {
        if ($state -ne 'absent') { & wsl @dockerArgs rm -f $container | Out-Null }
        @('bind 0.0.0.0', 'port 6379', 'protected-mode no', 'save ""', 'appendonly no', 'daemonize no', "dir $linuxRun/redis", 'logfile ""', 'databases 16') |
            Set-Content -Encoding ascii -LiteralPath (Join-Path $run 'redis\redis.conf')
        $image = (& wsl @dockerArgs inspect redis-local --format '{{.Image}}').Trim()
        if ($LASTEXITCODE -ne 0) { throw '无法取得本机 redis-local 镜像' }
        & wsl @dockerArgs run --detach --rm --name $container --read-only --log-driver none --cap-drop ALL --security-opt no-new-privileges --user 1000:1000 --workdir "$linuxRun/redis" --env TMPDIR=/tmp --env TEMP=/tmp --env TMP=/tmp --publish "127.0.0.1:${redisPort}:6379" --mount "type=bind,src=$linuxRun/redis,dst=$linuxRun/redis" --mount "type=bind,src=$linuxRun/container-tmp,dst=/tmp" --entrypoint redis-server $image "$linuxRun/redis/redis.conf" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw '测试 Redis 启动失败' }
    }
    & wsl @dockerArgs exec $container redis-cli PING | Out-Null
    if ($LASTEXITCODE -ne 0) { throw '测试 Redis 健康检查失败' }
    $image = (& wsl @dockerArgs inspect $container --format '{{.Image}}').Trim()
    $version = (& wsl @dockerArgs exec $container redis-server --version).Trim()
    $resources = @{
        mysql_port = $mysqlPort
        mysql_datadir = $datadir
        redis_container = $container
        redis_port = $redisPort
        redis_dir = "$linuxRun/redis"
        redis_image = $image
        redis_version = $version
    }
    [IO.File]::WriteAllText($manifest, ($resources | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
    Write-Output "测试库就绪：MySQL $mysqlPort，Redis $redisPort"
}

function Stop-Resources {
    if (Test-Port $mysqlPort) {
        & (Join-Path $mysqlBin 'mysqladmin.exe') --host=127.0.0.1 --port=$mysqlPort --user=root --connect-timeout=3 shutdown
        if ($LASTEXITCODE -ne 0) { throw 'MySQL 停止失败' }
    }
    if ((Get-RedisState) -ne 'absent') { & wsl @dockerArgs stop --timeout 10 $container | Out-Null }
    if (Test-Path $keepalive) {
        Stop-Process -Id ([int](Get-Content $keepalive)) -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $keepalive
    }
    Write-Output '测试库已停止，数据目录保留，可再次 start'
}

function Set-TestEnvironment {
    $mysqlUrl = "mysql+aiomysql://root@127.0.0.1:$mysqlPort/$database" + '?charset=utf8mb4'
    $redis = @{host = '127.0.0.1'; port = $redisPort}
    $cache = @{host = '127.0.0.1'; port = $redisPort; clients = @(@{name = 'default'; db = 0}, @{name = 'second'; db = 1})}
    $env:DUSHAN_SYSTEM_RESOURCES = $manifest
    $env:DUSHAN_CACHE_TEST_REDIS = $cache | ConvertTo-Json -Compress -Depth 5
    $env:DUSHAN_AUTH_TEST_REDIS = $redis | ConvertTo-Json -Compress
    $env:DUSHAN_SECURITY_TEST_REDIS = $redis | ConvertTo-Json -Compress
    $env:DUSHAN_DP_REDIS_PORT = [string]$redisPort
    $env:DUSHAN_DP_REPORT_DIR = Join-Path $run 'reports'
    $env:DUSHAN_DATABASE_TEST_URLS = ConvertTo-Json -Compress -InputObject @(@{name = 'mysql'; url = $mysqlUrl})
    $env:DUSHAN_SECURITY_MYSQL = @{url = $mysqlUrl} | ConvertTo-Json -Compress
    $env:DUSHAN_REDIS_FAULT_CONTAINER = $container
    $env:DUSHAN_MQ_TARGETS = '{}'
    $env:DUSHAN_HTTP_REPORT = $null
    $env:PYTEST_ADDOPTS = $null
}

switch ($Action) {
    'start' { Start-Resources }
    'stop' { Stop-Resources }
    'status' {
        "MySQL $mysqlPort 监听：$(Test-Port $mysqlPort)"
        "Redis 容器 ${container}：$(Get-RedisState)"
    }
    'run' {
        Start-Resources
        Set-TestEnvironment
        Set-Location $repo
        & (Join-Path $repo 'dushan-test\run-tests.ps1') -Paths $Paths -IncludeSmoke:$IncludeSmoke
        exit $LASTEXITCODE
    }
}
