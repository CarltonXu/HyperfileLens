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
    $ConfigDir = Join-Path $InstallDir "config"
    $ConfigPath = Join-Path $ConfigDir "config.yaml"
    $LogDir = Join-Path $env:ProgramData "HyperFileLens\logs"
    $ServiceName = "HyperFileLensProxy"

    $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run PowerShell as Administrator."
    }

    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

    $arch = if ([Environment]::Is64BitOperatingSystem) { "amd64" } else { "386" }
    if ($arch -ne "amd64") {
        throw "Only Windows amd64 is currently supported."
    }

    $tarUrl = "$Server/downloads/packages/proxy/hyperfilelens-proxy-windows-$arch.exe.tar.gz"
    $zipUrl = "$Server/downloads/packages/proxy/hyperfilelens-proxy-windows-$arch.exe.zip"
    $exeUrl = "$Server/downloads/packages/proxy/hyperfilelens-proxy-windows-$arch.exe"
    $tmpTar = Join-Path $env:TEMP "hyperfilelens-proxy.tar.gz"
    $tmpZip = Join-Path $env:TEMP "hyperfilelens-proxy.zip"
    $exePath = Join-Path $InstallDir "hyperfilelens-proxy.exe"

    Write-Host "[INFO] Downloading HyperFileLens proxy..."
    $downloaded = $false
    $downloadErrors = New-Object System.Collections.Generic.List[string]
    try {
        Invoke-WebRequest -Uri $tarUrl -OutFile $tmpTar -UseBasicParsing -ErrorAction Stop
        tar -xzf $tmpTar -C $InstallDir
        $candidate = Get-ChildItem -Path $InstallDir -Recurse -Filter "hyperfilelens-proxy*.exe" | Select-Object -First 1
        if (-not $candidate) { throw "Proxy package does not contain executable" }
        if ($candidate.FullName -ne $exePath) {
            Copy-Item $candidate.FullName $exePath -Force
        }
        $downloaded = $true
    } catch {
        $downloadErrors.Add("${tarUrl}: $($_.Exception.Message)") | Out-Null
        Write-Host "[WARN] tar.gz package download failed, trying zip/direct exe..."
        try {
            Invoke-WebRequest -Uri $zipUrl -OutFile $tmpZip -UseBasicParsing -ErrorAction Stop
            Expand-Archive -Path $tmpZip -DestinationPath $InstallDir -Force
            $candidate = Get-ChildItem -Path $InstallDir -Recurse -Filter "hyperfilelens-proxy*.exe" | Select-Object -First 1
            if (-not $candidate) { throw "Proxy zip does not contain executable" }
            if ($candidate.FullName -ne $exePath) {
                Copy-Item $candidate.FullName $exePath -Force
                # Remove the original file to avoid duplicates
                Remove-Item $candidate.FullName -Force -ErrorAction SilentlyContinue
            }
            $downloaded = $true
        } catch {
            $downloadErrors.Add("${zipUrl}: $($_.Exception.Message)") | Out-Null
            try {
                Invoke-WebRequest -Uri $exeUrl -OutFile $exePath -UseBasicParsing -ErrorAction Stop
                $downloaded = $true
            } catch {
                $downloadErrors.Add("${exeUrl}: $($_.Exception.Message)") | Out-Null
            }
        }
    } finally {
        Remove-Item $tmpTar -Force -ErrorAction SilentlyContinue
        Remove-Item $tmpZip -Force -ErrorAction SilentlyContinue
    }
    if (-not $downloaded) {
        $details = ($downloadErrors | ForEach-Object { "  - $_" }) -join [Environment]::NewLine
        throw "Failed to download HyperFileLens proxy package. Publish the Windows proxy package on the control plane and retry.$([Environment]::NewLine)$details"
    }

    if (-not $SkipKopia) {
        $kopia = Get-Command kopia -ErrorAction SilentlyContinue
        if ($kopia) {
            Write-Host "[INFO] Kopia already installed: $($kopia.Source)"
        } else {
            # Try to download from control server first
            $kopiaVersion = "0.22.3"
            $kopiaZipUrl = "$Server/downloads/packages/kopia/kopia-${kopiaVersion}-windows-x64.zip"
            $kopiaTempZip = Join-Path $env:TEMP "kopia.zip"
            $kopiaInstalled = $false

            Write-Host "[INFO] Downloading Kopia v${kopiaVersion} from control server..."
            try {
                Invoke-WebRequest -Uri $kopiaZipUrl -OutFile $kopiaTempZip -UseBasicParsing -ErrorAction Stop
                Expand-Archive -Path $kopiaTempZip -DestinationPath $InstallDir -Force
                Remove-Item $kopiaTempZip -Force -ErrorAction SilentlyContinue
                # Find kopia.exe in subdirectory and move to InstallDir root
                $kopiaExe = Get-ChildItem -Path $InstallDir -Recurse -Filter "kopia.exe" | Select-Object -First 1
                if ($kopiaExe) {
                    $kopiaDir = $kopiaExe.DirectoryName
                    if ($kopiaDir -ne $InstallDir) {
                        # Move all files from subdirectory to InstallDir
                        Get-ChildItem -Path $kopiaDir -File | Move-Item -Destination $InstallDir -Force
                        # Clean up empty subdirectory
                        Remove-Item $kopiaDir -Force -Recurse -ErrorAction SilentlyContinue
                    }
                    $env:Path = "$($InstallDir);$env:Path"
                    Write-Host "[INFO] Kopia installed successfully."
                    $kopiaInstalled = $true
                }
            } catch {
                Write-Host "[WARN] Failed to download Kopia from control server: $($_.Exception.Message)"
            }

            if (-not $kopiaInstalled) {
                # Try winget
                if (Get-Command winget -ErrorAction SilentlyContinue) {
                    Write-Host "[INFO] Installing Kopia with winget..."
                    winget install Kopia.Kopia --accept-package-agreements --accept-source-agreements
                } else {
                    Write-Host "[WARN] Kopia is not installed. Install Kopia manually if backup tasks need it."
                }
            }
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

    $wsProtocol = if ($Server.StartsWith("https")) { "wss" } else { "ws" }
    $displayName = if ($Name) { $Name } else { $hostname }
    $kopiaPath = (Get-Command kopia -ErrorAction SilentlyContinue).Source
    if (-not $kopiaPath) { $kopiaPath = "kopia.exe" }

    # Convert Windows paths to forward slashes for YAML compatibility
    $installDirUnix = $InstallDir -replace '\\', '/'
    $logDirUnix = $LogDir -replace '\\', '/'
    $kopiaPathUnix = $kopiaPath -replace '\\', '/'

    $configContent = @"
version: "$Version"
role: "$Role"

server:
  url: "$Server"
  api_token: ""
  ws_protocol: "$wsProtocol"
  reconnect_delay: 5s
  heartbeat_interval: 10s

agent:
  id: "$ProxyId"
  name: "$displayName"
  hostname: "$hostname"
  install_token: "$Token"

kopia:
  path: "$kopiaPathUnix"
  cache_path: "$installDirUnix/cache"

mount:
  enabled: false

logging:
  level: "info"
  file: "$logDirUnix/proxy.log"
"@
    # Save with UTF-8 BOM so Windows Notepad shows correctly
    $utf8Bom = New-Object System.Text.UTF8Encoding $true
    [System.IO.File]::WriteAllText($ConfigPath, $configContent, $utf8Bom)

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

    Start-Service -Name $ServiceName -ErrorAction Continue
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($service.Status -eq "Running") {
        Write-Host "[SUCCESS] HyperFileLens proxy installed and running."
    } else {
        Write-Host "[WARN] Service created but not running. Check logs: $LogDir\proxy.log"
        # Try to get more error info
        $wmiService = Get-WmiObject -Class Win32_Service -Filter "Name='$ServiceName'" -ErrorAction SilentlyContinue
        if ($wmiService) {
            Write-Host "[ERROR] Exit Code: $($wmiService.ExitCode), State: $($wmiService.State)"
        }
    }
    Write-Host "Status: Get-Service $ServiceName"
    Write-Host "Logs: $LogDir\proxy.log"
}
