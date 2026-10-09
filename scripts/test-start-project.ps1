# Launcher readiness unit tests. No services, credentials, or browser are touched.
$ErrorActionPreference = 'Stop'
$tokens = $null; $parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'start-project.ps1'), [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw 'Launcher syntax errors.' }
foreach ($node in $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $false)) {
    . ([ScriptBlock]::Create($node.Extent.Text))
}
class TestResponse : System.Net.WebResponse {
    [int]$StatusCode
    TestResponse([int]$status) { $this.StatusCode = $status }
}
$script:status = 422
$script:page = '<script type="module" src="/src/main.ts"></script>'
$script:backendValid = $true
function Invoke-WebRequest {
    [CmdletBinding()]
    param([string]$Uri, [string]$Method, [string]$ContentType, [string]$Body, [switch]$UseBasicParsing, [int]$TimeoutSec)
    if ($Method -eq 'Post') {
        if ($Body -ne '{}' -or $Uri -ne 'http://localhost:5173/api/auth/login') { throw 'Probe must not use credentials.' }
        throw [System.Net.WebException]::new('Test HTTP status', $null, [System.Net.WebExceptionStatus]::ProtocolError, [TestResponse]::new($script:status))
    }
    return [pscustomobject]@{ StatusCode = 200; Content = $script:page }
}
function Invoke-RestMethod {
    [CmdletBinding()]
    param([string]$Uri, [int]$TimeoutSec)
    if ($script:backendValid) { return [pscustomobject]@{ paths = [pscustomobject]@{ '/api/auth/login' = @{}; '/api/ai/capabilities' = @{} } } }
    return [pscustomobject]@{ paths = [pscustomobject]@{} }
}
$count = 0
function Assert-Equal($Actual, $Expected, [string]$Name) {
    if ($Actual -ne $Expected) { throw "FAIL: $Name" }
    $script:count++
    Write-Host "PASS: $Name"
}
Assert-Equal (Test-Backend) $true 'Existing backend API recognized'
$script:backendValid = $false
Assert-Equal (Test-Backend) $false 'Unrelated backend rejected'
Assert-Equal (Test-Frontend) $true 'Vite plus backend validation recognized'
$script:status = 404
Assert-Equal (Test-Frontend) $false 'Missing proxy rejected'
$script:status = 502
Assert-Equal (Test-Frontend) $false 'Unavailable backend rejected'
$script:status = 401
Assert-Equal (Test-Frontend) $false 'Unexpected authentication response rejected'
$script:status = 422; $script:page = '<html>Unrelated service</html>'
Assert-Equal (Test-Frontend) $false 'Unrelated frontend rejected'
Write-Host "Tests passed: $count"
