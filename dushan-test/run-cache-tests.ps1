param(
    [Parameter(Mandatory = $true)][string]$RedisFile,
    [string[]]$Path = @('framework/starter_cache'),
    [string]$DatabaseTargets = '',
    [string]$Python = (Join-Path $PSScriptRoot '.venv/Scripts/python.exe')
)

$ErrorActionPreference = 'Stop'
$runRoot = Join-Path (Get-Location).Path ('Temp\cache-tests\' + (Get-Date -Format 'yyyyMMdd-HHmmssfff'))
New-Item -ItemType Directory -Path $runRoot -Force | Out-Null
$redis = [System.IO.File]::ReadAllText((Resolve-Path -LiteralPath $RedisFile).Path)
$null = ConvertFrom-Json -InputObject $redis
$settings = @{
    TEMP = $runRoot
    TMP = $runRoot
    TMPDIR = $runRoot
    PYTHONDONTWRITEBYTECODE = '1'
    PYTHONUTF8 = '1'
    PYTHONIOENCODING = 'utf-8'
    PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
    DUSHAN_CACHE_TEST_REDIS = $redis
}
if ($DatabaseTargets -ne '') {
    $targets = [System.IO.File]::ReadAllText((Resolve-Path -LiteralPath $DatabaseTargets).Path)
    $null = ConvertFrom-Json -InputObject $targets
    $settings['DUSHAN_DATABASE_TEST_URLS'] = $targets
}
$previous = @{}
try {
    foreach ($name in $settings.Keys) {
        $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        [Environment]::SetEnvironmentVariable($name, $settings[$name], 'Process')
    }
    $arguments = @('-B', '-m', 'pytest', '-p', 'pytest_asyncio.plugin', '-c', (Join-Path $PSScriptRoot 'pytest.ini'))
    foreach ($item in $Path) { $arguments += (Join-Path $PSScriptRoot $item) }
    $arguments += @('--basetemp', (Join-Path $runRoot 'fixtures'), '-o', ('cache_dir=' + (Join-Path $runRoot 'cache')),
                    '--junitxml', (Join-Path $runRoot 'results.xml'))
    $ErrorActionPreference = 'Continue'
    & $Python @arguments
    $result = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    Write-Output ('缓存测试报告：' + (Join-Path $runRoot 'results.xml'))
} finally {
    foreach ($name in $previous.Keys) {
        [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process')
    }
}
exit $result
