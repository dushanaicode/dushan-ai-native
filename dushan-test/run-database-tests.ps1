param(
    [Parameter(Mandatory = $true)][string]$TargetsFile,
    [string]$Python = (Join-Path $PSScriptRoot '.venv/Scripts/python.exe')
)

$ErrorActionPreference = 'Stop'
$runRoot = Join-Path (Get-Location).Path ('Temp\database-tests\' + (Get-Date -Format 'yyyyMMdd-HHmmssfff'))
New-Item -ItemType Directory -Path $runRoot -Force | Out-Null
$targets = [System.IO.File]::ReadAllText((Resolve-Path -LiteralPath $TargetsFile).Path)
$null = ConvertFrom-Json -InputObject $targets
$settings = @{
    TEMP = $runRoot
    TMP = $runRoot
    TMPDIR = $runRoot
    PYTHONDONTWRITEBYTECODE = '1'
    PYTHONUTF8 = '1'
    PYTHONIOENCODING = 'utf-8'
    PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
    DUSHAN_DATABASE_TEST_URLS = $targets
}
$previous = @{}
try {
    foreach ($name in $settings.Keys) {
        $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        [Environment]::SetEnvironmentVariable($name, $settings[$name], 'Process')
    }
    $arguments = @('-B', '-m', 'pytest', '-p', 'pytest_asyncio.plugin', '-c', (Join-Path $PSScriptRoot 'pytest.ini'),
                  (Join-Path $PSScriptRoot 'framework/starter_database'),
                  '--basetemp', (Join-Path $runRoot 'fixtures'), '-o', ('cache_dir=' + (Join-Path $runRoot 'cache')),
                  '--junitxml', (Join-Path $runRoot 'results.xml'))
    $ErrorActionPreference = 'Continue'
    & $Python @arguments
    $result = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    Write-Output ('数据库测试报告：' + (Join-Path $runRoot 'results.xml'))
} finally {
    foreach ($name in $previous.Keys) {
        [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process')
    }
}
exit $result
