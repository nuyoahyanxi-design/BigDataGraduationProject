[CmdletBinding()]
param(
    [ValidateSet('backend', 'frontend')][string]$Service,
    [string]$ProjectRoot = '',
    [string]$Distro = 'Ubuntu-22.04-Recovered',
    [ValidateRange(5, 1800)][int]$WaitTimeoutSeconds = 300,
    [switch]$NoBrowser,
    [switch]$NoPause,
    [switch]$CheckOnly,
    [switch]$ConfigureOnly
)
$ErrorActionPreference = 'Stop'
$launcherPath = $MyInvocation.MyCommand.Path
if (-not $ProjectRoot) { $ProjectRoot = Split-Path (Split-Path $launcherPath -Parent) -Parent }
function Set-AgnesWslEnvironment {
    # WSLENV contains variable names only; Key is never passed as a command argument.
    $names = @('AGNES_MODEL','AGNES_MODEL_ID','AGNES_API_KEY','APP_ENV','AI_ALLOWED_RESOURCE_IDS','HTTP_PROXY','HTTPS_PROXY','NO_PROXY','WINDOWS_PROXY_PORT')
    $parts = @($env:WSLENV -split ':' | Where-Object { $_ -and ($_ -split '/')[0] -notin $names })
    foreach ($name in $names) {
        if ([Environment]::GetEnvironmentVariable($name)) { $parts += $name }
    }
    $env:WSLENV = $parts -join ':'
}
function Initialize-LocalConfig {
    Set-AgnesWslEnvironment
    & wsl.exe -d $Distro --cd $ProjectRoot --exec bash scripts/start-project-service.sh configure
    if ($LASTEXITCODE -ne 0) { throw 'Agnes configuration is missing or invalid. Check the configuration messages; no backend was started.' }
    Write-Host 'Local Agnes configuration ready; Git ignored and Key not displayed.'
}
function Read-Json([string]$Url) {
    try { return Invoke-RestMethod -Uri $Url -TimeoutSec 5 -ErrorAction Stop } catch { return $null }
}
function Test-Backend {
    $schema = Read-Json 'http://127.0.0.1:8000/openapi.json'
    return ($null -ne $schema -and $null -ne $schema.paths -and $schema.paths.PSObject.Properties.Name -contains '/api/auth/login' -and $schema.paths.PSObject.Properties.Name -contains '/api/ai/capabilities')
}
function Test-Frontend {
    try {
        $page = Invoke-WebRequest 'http://127.0.0.1:5173/' -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        if ($page.StatusCode -ne 200 -or $page.Content -notmatch '/src/main.ts') { return $false }
        # Missing credentials must reach backend validation, without logging in.
        try {
            Invoke-WebRequest 'http://127.0.0.1:5173/api/auth/login' -Method Post -ContentType 'application/json' -Body '{}' -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop | Out-Null
            return $false
        } catch {
            return ($null -ne $_.Exception.Response -and [int]$_.Exception.Response.StatusCode -eq 422)
        }
    } catch { return $false }
}
function Test-Port([int]$Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $task = $client.ConnectAsync('127.0.0.1', $Port)
        return ($task.Wait(500) -and $client.Connected)
    } catch { return $false } finally { $client.Dispose() }
}
function Start-ServiceWindow([string]$Name) {
    $arguments = '-NoExit -NoProfile -File "{0}" -Service {1} -ProjectRoot "{2}" -Distro "{3}"' -f $launcherPath, $Name, $ProjectRoot, $Distro
    # Visible terminals allow hidden Key input and Ctrl+C shutdown.
    Start-Process powershell.exe -ArgumentList $arguments -WindowStyle Normal | Out-Null
}
try {
    if ($ConfigureOnly) {
        Initialize-LocalConfig
        Write-Host 'Configuration complete. Double-click start-project.bat for normal startup.'
        if (-not $NoPause) { Read-Host 'Press Enter to close' | Out-Null }
        exit 0
    }
    if ($Service) {
        $Host.UI.RawUI.WindowTitle = "Spark Learning - $Service"
        if ($Service -eq 'backend') { Initialize-LocalConfig }
        if ($Service -eq 'backend') {
            if (-not $env:WINDOWS_PROXY_PORT) {
                $proxyListener = Get-NetTCPConnection -State Listen -LocalPort 7890 -ErrorAction SilentlyContinue
                if ($proxyListener) { $env:WINDOWS_PROXY_PORT = '7890' }
            }
            Set-AgnesWslEnvironment
        }
        & wsl.exe -d $Distro --cd $ProjectRoot --exec bash scripts/start-project-service.sh $Service
        if ($LASTEXITCODE -ne 0) { throw "WSL $Service exited with code $LASTEXITCODE. Check this terminal." }
        exit 0
    }
    Write-Host 'Spark Learning: checking local development services...'
    Get-Command wsl.exe -ErrorAction Stop | Out-Null
    if ((Get-Service MySQL80 -ErrorAction Stop).Status -ne 'Running') {
        throw 'MySQL80 is not running. Start it in Windows Services, then retry.'
    }
    & wsl.exe -d $Distro --cd $ProjectRoot --exec bash -c 'test -f environments/activate-bigdata.sh && test -f outputs/start-ai-real-model-secure.py && test -f frontend/package.json && test -f scripts/start-project-service.sh'
    if ($LASTEXITCODE -ne 0) { throw 'WSL distribution, project path, or required launcher files are unavailable.' }
    $backendReady = Test-Backend
    $frontendReady = Test-Frontend
    if ($CheckOnly) {
        Write-Host "Backend ready: $backendReady; frontend and proxy ready: $frontendReady"
        if (-not ($backendReady -and $frontendReady)) { throw 'Readiness check failed.' }
    } else {
        if (-not $backendReady -and (Test-Port 8000)) { throw 'Port 8000 is occupied by an unavailable or unrelated service. Check it manually; nothing was stopped.' }
        if (-not $frontendReady -and (Test-Port 5173)) { throw 'Port 5173 is occupied or its /api proxy is unavailable. Check that terminal; nothing was stopped.' }
        if ($backendReady) { Write-Host 'Reusing existing FastAPI.' } else {
            Write-Host 'Opening backend terminal. First startup saves .env.local securely; later starts reuse it. Key input stays hidden.'
            Start-ServiceWindow 'backend'
        }
        if ($frontendReady) { Write-Host 'Reusing existing Vite and API proxy.' } else {
            Write-Host 'Opening frontend terminal.'
            Start-ServiceWindow 'frontend'
        }
        $deadline = [DateTime]::UtcNow.AddSeconds($WaitTimeoutSeconds)
        while (-not ($backendReady -and $frontendReady)) {
            if ([DateTime]::UtcNow -ge $deadline) { throw 'Startup timed out. Check the two service terminals and complete secure input. They remain open for diagnosis.' }
            Start-Sleep -Seconds 2
            $backendReady = Test-Backend
            $frontendReady = Test-Frontend
        }
        Write-Host 'Ready: http://127.0.0.1:5173 (backend and /api proxy verified).'
        if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:5173' | Out-Null }
    }
    Write-Host 'Close service terminals with Ctrl+C. This launcher does not stop MySQL or WSL.'
    if (-not $NoPause) { Read-Host 'Press Enter to close this launcher' | Out-Null }
    exit 0
} catch {
    Write-Host ('Startup failed: ' + $_.Exception.Message) -ForegroundColor Red
    if (-not $NoPause) { Read-Host 'Press Enter to close this launcher' | Out-Null }
    exit 1
}

