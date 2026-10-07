param(
    [string]$Python = (Join-Path $PSScriptRoot '.venv/Scripts/python.exe'),
    [string[]]$Paths = @('server', 'framework', 'module_system', 'module_infra'),
    [string]$TempRoot = (Join-Path (Get-Location).Path 'Temp\dushan-tests'),
    [switch]$IncludeSmoke
)

$ErrorActionPreference = 'Stop'
$runRoot = Join-Path ($ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($TempRoot)) (Get-Date -Format 'yyyyMMdd-HHmmssfff')
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
    $testPaths = @($Paths | ForEach-Object { Join-Path $PSScriptRoot $_ })
    $arguments = @('-B', '-m', 'pytest', '-p', 'pytest_asyncio.plugin', '-c', (Join-Path $PSScriptRoot 'pytest.ini')) +
                 $testPaths + @('--basetemp', (Join-Path $runRoot 'fixtures'), '-o', ('cache_dir=' + (Join-Path $runRoot 'cache')),
                 '--junitxml', (Join-Path $runRoot 'results.xml'))
    if (-not $IncludeSmoke) { $arguments += @('-m', 'not smoke') }
    $ErrorActionPreference = 'Continue'
    & $Python @arguments
    $result = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    Write-Output ('JUnit report: ' + (Join-Path $runRoot 'results.xml'))
} finally {
    foreach ($name in $previous.Keys) { [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process') }
}
exit $result
