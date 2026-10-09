# Windows-only safety checks, using fake values in an isolated temporary folder.
$ErrorActionPreference = 'Stop'
$tokens = $null; $errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'start-project.ps1'), [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw 'PowerShell parse errors' }
foreach ($node in $ast.FindAll({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst]}, $false)) {
    if ($node.Name -in @('Set-AgnesWslEnvironment')) { . ([ScriptBlock]::Create($node.Extent.Text)) }
}
$old = @{}
foreach ($name in @('WSLENV','AGNES_MODEL','AGNES_MODEL_ID','AGNES_API_KEY','APP_ENV','AI_ALLOWED_RESOURCE_IDS','HTTP_PROXY','HTTPS_PROXY','NO_PROXY','WINDOWS_PROXY_PORT')) { $old[$name] = [Environment]::GetEnvironmentVariable($name) }
$ProjectRoot = Join-Path ([IO.Path]::GetTempPath()) ('agnes-config-test-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $ProjectRoot | Out-Null
try {
    $env:WSLENV = 'OTHER/u:AGNES_API_KEY/p'
    $env:AGNES_MODEL = 'test-model'; $env:AGNES_MODEL_ID = 'alias-model'; $env:AGNES_API_KEY = 'nonsecret-test-placeholder'
    $env:APP_ENV = 'development'; $env:AI_ALLOWED_RESOURCE_IDS = '*'
    $env:HTTP_PROXY = 'http://127.0.0.1:7890'; $env:HTTPS_PROXY = $env:HTTP_PROXY
    $env:NO_PROXY = 'localhost,127.0.0.1'; $env:WINDOWS_PROXY_PORT = '7890'
    Set-AgnesWslEnvironment
    if ($env:WSLENV -ne 'OTHER/u:AGNES_MODEL:AGNES_MODEL_ID:AGNES_API_KEY:APP_ENV:AI_ALLOWED_RESOURCE_IDS:HTTP_PROXY:HTTPS_PROXY:NO_PROXY:WINDOWS_PROXY_PORT') { throw 'WSL variable forwarding failed' }
    if ($env:WSLENV -match 'nonsecret') { throw 'Values leaked into WSLENV' }
    Write-Host 'PASS: WSLENV forwards names only and removes invalid path conversion'
} finally {
    foreach ($name in $old.Keys) { [Environment]::SetEnvironmentVariable($name, $old[$name]) }
    Remove-Item -LiteralPath $ProjectRoot -Force
}
