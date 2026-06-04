function Install-HyperFileLensProxy {
    param(
        [Parameter(Mandatory=$true)][string]$ProxyId,
        [Parameter(Mandatory=$true)][ValidateSet("agent", "sync")][string]$Role,
        [Parameter(Mandatory=$true)][string]$Server,
        [Parameter(Mandatory=$true)][string]$Token,
        [string]$Name = "",
        [switch]$SkipKopia
    )

    $ErrorActionPreference = "Stop"
    $Version = "1.0.0"
    $Server = $Server.TrimEnd("/")
    $InstallDir = Join-Path $env:ProgramFiles "HyperFileLens\Proxy"
    $ConfigPath = Join-Path $InstallDir "config.yaml"
    $LogDir = Join-Path $env:ProgramData "HyperFileLens\logs"
    $ServiceName = "HyperFileLensProxy"

    $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run PowerShell as Administrator."
    }

    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

    $arch = if ([Environment]::Is64BitOperatingSystem) { "amd64" } else { "386" }
    if ($arch -ne "amd64") {
        throw "Only Windows amd64 is currently supported."
    }

    $tarUrl = "$Server/downloads/packages/proxy/hyperfilelens-proxy-windows-$arch.exe.tar.gz"
    $zipUrl = "$Server/downloads/packages/proxy/hyperfilelens-proxy-windows-$arch.zip"
    $exeUrl = "$Server/downloads/packages/proxy/hyperfilelens-proxy-windows-$arch.exe"
    $tmpTar = Join-Path $env:TEMP "hyperfilelens-proxy.tar.gz"
    $tmpZip = Join-Path $env:TEMP "hyperfilelens-proxy.zip"
    $exePath = Join-Path $InstallDir "hyperfilelens-proxy.exe"

    Write-Host "[INFO] Downloading HyperFileLens proxy..."
    try {
        Invoke-WebRequest -Uri $tarUrl -OutFile $tmpTar -UseBasicParsing
        tar -xzf $tmpTar -C $InstallDir
        $candidate = Get-ChildItem -Path $InstallDir -Recurse -Filter "hyperfilelens-proxy*.exe" | Select-Object -First 1
        if (-not $candidate) { throw "Proxy package does not contain executable" }
        if ($candidate.FullName -ne $exePath) {
            Copy-Item $candidate.FullName $exePath -Force
        }
    } catch {
        Write-Host "[WARN] tar.gz package download failed, trying zip/direct exe..."
        try {
            Invoke-WebRequest -Uri $zipUrl -OutFile $tmpZip -UseBasicParsing
            Expand-Archive -Path $tmpZip -DestinationPath $InstallDir -Force
            $candidate = Get-ChildItem -Path $InstallDir -Recurse -Filter "hyperfilelens-proxy*.exe" | Select-Object -First 1
            if (-not $candidate) { throw "Proxy zip does not contain executable" }
            if ($candidate.FullName -ne $exePath) {
                Copy-Item $candidate.FullName $exePath -Force
            }
        } catch {
            Invoke-WebRequest -Uri $exeUrl -OutFile $exePath -UseBasicParsing
        }
    } finally {
        Remove-Item $tmpTar -Force -ErrorAction SilentlyContinue
        Remove-Item $tmpZip -Force -ErrorAction SilentlyContinue
    }

    if (-not $SkipKopia) {
        $kopia = Get-Command kopia -ErrorAction SilentlyContinue
        if ($kopia) {
            Write-Host "[INFO] Kopia already installed: $($kopia.Source)"
        } elseif (Get-Command winget -ErrorAction SilentlyContinue) {
            Write-Host "[INFO] Installing Kopia with winget..."
            winget install Kopia.Kopia --accept-package-agreements --accept-source-agreements
        } else {
            Write-Host "[WARN] Kopia is not installed and winget is unavailable. Install Kopia manually if backup tasks need it."
        }
    }

    $hostname = $env:COMPUTERNAME
    $ip = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
        Select-Object -First 1 -ExpandProperty IPAddress)
    if (-not $ip) { $ip = "" }
    $cpu = [Environment]::ProcessorCount
    $memory = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
    $disk = (Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'").Size
    $osVersion = (Get-CimInstance Win32_OperatingSystem).Caption
    $kopiaVersion = ""
    if (Get-Command kopia -ErrorAction SilentlyContinue) {
        $kopiaVersion = (kopia --version 2>$null | Select-Object -First 1)
    }

    Write-Host "[INFO] Registering proxy..."
    $body = @{
        proxy_id = $ProxyId
        install_token = $Token
        hostname = $hostname
        internal_ip = $ip
        os = "windows"
        os_version = $osVersion
        version = $Version
        kopia_version = $kopiaVersion
        cpu_cores = $cpu
        memory_total = [int64]$memory
        disk_total = [int64]$disk
        capabilities = @{}
    } | ConvertTo-Json -Depth 5

    $registration = Invoke-RestMethod -Method Post -Uri "$Server/api/v1/proxies/register/" -ContentType "application/json" -Body $body
    $apiToken = $registration.api_token
    if (-not $apiToken) {
        throw "Registration did not return api_token."
    }

    $wsProtocol = if ($Server.StartsWith("https")) { "wss" } else { "ws" }
    $displayName = if ($Name) { $Name } else { $hostname }
    $kopiaPath = (Get-Command kopia -ErrorAction SilentlyContinue).Source
    if (-not $kopiaPath) { $kopiaPath = "kopia.exe" }

    @"
version: "$Version"
role: "$Role"

server:
  url: "$Server"
  api_token: "$apiToken"
  ws_protocol: "$wsProtocol"
  reconnect_delay: 5s
  heartbeat_interval: 10s

agent:
  id: "$ProxyId"
  name: "$displayName"
  hostname: "$hostname"

kopia:
  path: "$kopiaPath"
  cache_path: "$InstallDir\cache"

mount:
  enabled: false

logging:
  level: "info"
  file: "$LogDir\proxy.log"
"@ | Set-Content -Path $ConfigPath -Encoding UTF8

    if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
        Stop-Service -Name $ServiceName -ErrorAction SilentlyContinue
        sc.exe delete $ServiceName | Out-Null
        Start-Sleep -Seconds 1
    }

    New-Service `
        -Name $ServiceName `
        -BinaryPathName "`"$exePath`" --config `"$ConfigPath`"" `
        -DisplayName "HyperFileLens Proxy" `
        -StartupType Automatic `
        -Description "HyperFileLens source-side proxy agent"

    Start-Service -Name $ServiceName
    Write-Host "[SUCCESS] HyperFileLens proxy installed."
    Write-Host "Status: Get-Service $ServiceName"
    Write-Host "Logs: $LogDir\proxy.log"
}
