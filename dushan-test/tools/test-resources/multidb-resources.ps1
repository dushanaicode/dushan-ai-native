param(
    [Parameter(Mandatory = $true)][ValidateSet('start', 'stop', 'status')][string]$Action,
    [string[]]$Databases = @('postgresql', 'opengauss', 'kingbase', 'tidb', 'oceanbase', 'dm')
)

# 多数据库测试实例：容器只读运行，数据全部放在内存盘，停止后不留数据；
# 不写入 WSL 的 Docker 数据目录，CLI 状态放在仓库 Temp 下。

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$run = Join-Path $repo 'Temp\multidb'
$linuxRepo = '/mnt/' + $repo.Substring(0, 1).ToLower() + ($repo.Substring(2) -replace '\\', '/')
$linuxRun = $linuxRepo + '/Temp/multidb'
$linuxTools = $linuxRepo + '/dushan-test/tools/test-resources/multidb'
$manifest = Join-Path $run 'resources.json'
$password = 'Multidb@2026'
$obPassword = 'Multidb2026'
$env:TEMP = $run
$env:TMP = $run
$env:TMPDIR = $run
New-Item -ItemType Directory -Path (Join-Path $run 'docker-cli') -Force | Out-Null
$docker = @('-d', 'Ubuntu-24.04', '-u', 'root', '--exec', 'env', "TMPDIR=$linuxRun", "TEMP=$linuxRun", "TMP=$linuxRun", 'docker', '--config', "$linuxRun/docker-cli")
$common = @('--read-only', '--log-driver', 'none', '--tmpfs', '/tmp:rw,exec')

# 传给外部程序的参数里，内层双引号写成 \"，Windows PowerShell 5.1 否则会丢掉它们。
$specs = [ordered]@{
    postgresql = @{
        Port = 35432
        Args = @('--tmpfs', '/var/lib/postgresql/data:rw,size=2g,uid=999,gid=999', '--tmpfs', '/var/run/postgresql:rw,uid=999,gid=999',
                 '-e', "POSTGRES_PASSWORD=$password", '-e', 'POSTGRES_DB=native', '-p', '127.0.0.1:35432:5432', 'local/dushan-pgvector:0.8.6-pg17.11')
        Ready = @('pg_isready', '-U', 'postgres', '-d', 'native')
        Url = 'postgresql+asyncpg://postgres:Multidb%402026@127.0.0.1:35432/native'
    }
    opengauss = @{
        Port = 35433
        Args = @('--cap-add', 'SYS_NICE', '--shm-size', '1g', '--tmpfs', '/var/lib/opengauss:rw,size=3g', '--tmpfs', '/var/run/opengauss:rw',
                 '-e', "GS_PASSWORD=$password", '-p', '127.0.0.1:35433:5432', 'opengauss:6.0.5')
        Ready = @('su', '-', 'omm', '-c', 'gsql -d postgres -p 5432 -c \"SELECT 1\"')
        Init = @('su', '-', 'omm', '-c', "gsql -d postgres -p 5432 -c \`"CREATE DATABASE native OWNER gaussdb DBCOMPATIBILITY 'PG'\`"")
        Url = 'opengauss+asyncpg://gaussdb:Multidb%402026@127.0.0.1:35433/native'
    }
    kingbase = @{
        Port = 35434
        Args = @('--shm-size', '1g', '--tmpfs', '/kb:rw,exec,size=4g,uid=1000,gid=1000',
                 '--mount', "type=bind,src=$linuxTools/kingbase-start.sh,dst=/kb-start.sh,readonly", '--entrypoint', '/bin/bash',
                 '-e', "DB_PASSWORD=$password", '-e', 'DB_MODE=pg', '-e', 'DB_USER=kingbase', '-p', '127.0.0.1:35434:54321',
                 'kingbase_v009r001c010b0004_single_x86:v1', '/kb-start.sh')
        Ready = @('bash', '-c', 'echo > /dev/tcp/127.0.0.1/54321')
        Init = @('bash', '-c', 'LD_LIBRARY_PATH=/kb/kingbase/lib /kb/kingbase/bin/ksql -U kingbase -d test -p 54321 -c \"CREATE DATABASE native\"')
        Url = 'kingbase+asyncpg://kingbase:Multidb%402026@127.0.0.1:35434/native'
    }
    tidb = @{
        Port = 34000
        Args = @('--tmpfs', '/data:rw,size=3g', '-e', 'GOMEMLIMIT=1GiB', '-p', '127.0.0.1:34000:4000', 'pingcap/tidb:v8.5.3',
                 '--store=unistore', '--path=/data', '--host=0.0.0.0', '-P', '4000', '--status=10080', '--log-slow-query=/tmp/tidb-slow.log')
        Url = 'mysql+aiomysql://root@127.0.0.1:34000/native?charset=utf8mb4'
    }
    oceanbase = @{
        Port = 32881
        Args = @('--ulimit', 'nofile=65536:65536', '--ulimit', 'stack=-1:-1', '--tmpfs', '/root/ob:rw,exec,size=12g', '--tmpfs', '/obhome:rw,exec,size=3g',
                 '--tmpfs', '/run:rw', '--tmpfs', '/var/run:rw',
                 '--mount', "type=bind,src=$linuxTools/oceanbase-init.sql,dst=/etc/native-init/010-native.sql,readonly",
                 '--mount', "type=bind,src=$linuxTools/oceanbase-start.sh,dst=/ob-start.sh,readonly", '--entrypoint', '/bin/bash',
                 '-e', 'MODE=mini', '-e', 'OB_MEMORY_LIMIT=6G', '-e', 'OB_SYSTEM_MEMORY=1G', '-e', 'OB_DATAFILE_SIZE=3G', '-e', 'OB_LOG_DISK_SIZE=4G',
                 '-e', 'OB_TENANT_MEMORY_SIZE=2G', '-e', 'OB_TENANT_LOG_DISK_SIZE=2G', '-e', 'OB_TENANT_MIN_CPU=1', '-e', 'OB_TENANT_INIT_SQL_DIR=/etc/native-init',
                 '-e', "OB_TENANT_PASSWORD=$obPassword", '-e', "OB_SYS_PASSWORD=$obPassword", '-p', '127.0.0.1:32881:2881',
                 'oceanbase/oceanbase-ce:4.3.5.4-104000042025090916', '/ob-start.sh')
        # mini 模式下测试租户只分到 1G 内存，装载全部建表与种子会超出租户内存上限，启动后调大资源单元。
        Ready = @('bash', '-c', "obclient -h127.1 -P2881 -uroot@test -p$obPassword -e 'SELECT 1'")
        Init = @('bash', '-c', "obclient -h127.1 -P2881 -uroot@sys -p$obPassword -e 'ALTER RESOURCE UNIT test_unit MEMORY_SIZE = 3221225472'")
        Url = "oceanbase+aiomysql://root%40test:$obPassword@127.0.0.1:32881/native?charset=utf8mb4"
    }
    # 达梦镜像由 multidb/dm8/Dockerfile 用官方 Linux 安装包本地构建，构建方法见该文件开头。
    dm = @{
        Port = 35236
        Args = @('--tmpfs', '/dmdata:rw,size=2g,uid=1000,gid=1000', '--tmpfs', '/opt/dmdbms/log:rw,uid=1000,gid=1000',
                 '-e', "DM_PASSWORD=$password", '-p', '127.0.0.1:35236:5236', 'local/dushan-dm8:20260710')
        Ready = @('bash', '-c', 'echo > /dev/tcp/127.0.0.1/5236')
        Url = 'dm+dushan_async://SYSDBA:Multidb%402026@127.0.0.1:35236'
    }
}

function Get-State([string]$Name) {
    $state = & wsl @docker ps --all --filter "name=^/dushan-multidb-$Name$" --format '{{.State}}'
    if ($LASTEXITCODE -ne 0) { throw '无法查询 Docker 容器状态' }
    if ($state) { $state.Trim() } else { 'absent' }
}

function Test-Port([int]$Port) {
    $client = [System.Net.Sockets.TcpClient]::new()
    try { $client.Connect('127.0.0.1', $Port); $true } catch [System.Net.Sockets.SocketException] { $false } finally { $client.Dispose() }
}

function Wait-Ready([string]$Name, $Spec) {
    # 就绪前检查命令会向 stderr 输出连接失败，这里只看退出码。
    $ErrorActionPreference = 'Continue'
    for ($i = 0; $i -lt 80; $i++) {
        if ($Spec.Ready) {
            & wsl @docker exec "dushan-multidb-$Name" @($Spec.Ready) 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0 -and (Test-Port $Spec.Port)) { return }
        } elseif (Test-Port $Spec.Port) {
            Start-Sleep -Seconds 3
            return
        }
        Start-Sleep -Seconds 5
    }
    throw "$Name 在限定时间内没有就绪"
}

function Write-Manifest {
    $targets = @()
    foreach ($name in $specs.Keys) {
        if ((Get-State $name) -eq 'running') { $targets += [ordered]@{ name = $name; url = $specs[$name].Url } }
    }
    [System.IO.File]::WriteAllText($manifest, (ConvertTo-Json -InputObject @($targets) -Depth 3), [System.Text.UTF8Encoding]::new($false))
    Write-Output "连接信息：$manifest"
}

switch ($Action) {
    'start' {
        & wsl -d Ubuntu-24.04 -u root --exec systemctl is-active docker | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'WSL 中的 Docker 未运行' }
        foreach ($name in $Databases) {
            $spec = $specs[$name]
            if (-not $spec) { throw "不支持的数据库：$name" }
            if ((Get-State $name) -ne 'running') {
                & wsl @docker run -d --rm --name "dushan-multidb-$name" @common @($spec.Args) | Out-Null
                if ($LASTEXITCODE -ne 0) { throw "$name 启动失败" }
                Wait-Ready $name $spec
                if ($name -eq 'tidb') {
                    & 'C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe' -h 127.0.0.1 -P 34000 -u root -e 'CREATE DATABASE IF NOT EXISTS native CHARACTER SET utf8mb4'
                    if ($LASTEXITCODE -ne 0) { throw 'TiDB 建库失败' }
                }
                if ($spec.Init) {
                    & wsl @docker exec "dushan-multidb-$name" @($spec.Init) | Out-Null
                    if ($LASTEXITCODE -ne 0) { throw "$name 初始化失败" }
                }
            }
            Write-Output "$name 已就绪：127.0.0.1:$($spec.Port)"
        }
        Write-Manifest
    }
    'stop' {
        foreach ($name in $Databases) {
            if ((Get-State $name) -ne 'absent') { & wsl @docker rm -f "dushan-multidb-$name" | Out-Null }
            Write-Output "$name 已停止"
        }
        Write-Manifest
    }
    'status' {
        foreach ($name in $specs.Keys) { Write-Output ("{0}: {1}" -f $name, (Get-State $name)) }
    }
}
