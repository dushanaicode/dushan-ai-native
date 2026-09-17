param(
    [string]$Python = (Join-Path $PSScriptRoot '.venv/Scripts/python.exe'),
    [switch]$IncludeSmoke
)

$ErrorActionPreference = 'Stop'
$runRoot = Join-Path (Get-Location).Path ('Temp\dushan-tests\' + (Get-Date -Format 'yyyyMMdd-HHmmssfff'))
New-Item -ItemType Directory -Path $runRoot -Force | Out-Null
$settings = @{
    TEMP = $runRoot
    TMP = $runRoot
    TMPDIR = $runRoot
    PYTHONDONTWRITEBYTECODE = '1'
    PYTHONUTF8 = '1'
    PYTHONIOENCODING = 'utf-8'
    PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
}
$previous = @{}
try {
    foreach ($name in $settings.Keys) {
        $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        [Environment]::SetEnvironmentVariable($name, $settings[$name], 'Process')
    }
    $arguments = @('-B', '-m', 'pytest', '-p', 'pytest_asyncio.plugin', '-c', (Join-Path $PSScriptRoot 'pytest.ini'),
                  (Join-Path $PSScriptRoot 'server'), (Join-Path $PSScriptRoot 'framework'), (Join-Path $PSScriptRoot 'module_system'), (Join-Path $PSScriptRoot 'module_infra'),
                  '--basetemp', (Join-Path $runRoot 'fixtures'), '-o', ('cache_dir=' + (Join-Path $runRoot 'cache')),
                  '--junitxml', (Join-Path $runRoot 'results.xml'))
    if (-not $IncludeSmoke) { $arguments += @('-m', 'not smoke') }
    $ErrorActionPreference = 'Continue'
    & $Python @arguments
    $result = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    Write-Output ('测试报告：' + (Join-Path $runRoot 'results.xml'))
} finally {
    foreach ($name in $previous.Keys) { [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process') }
}
exit $result
