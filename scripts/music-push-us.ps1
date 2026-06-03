# music-push-us.ps1
# US side: push desktop audio to VPS music channel
# Usage: .\scripts\music-push-us.ps1 [-Device "device name"] [-Bitrate 128k] [-Latency 500000]

param(
    [string]$Device,
    [string]$Bitrate = "128k",
    [int]$Latency = 500000
)

$ErrorActionPreference = "Stop"

function Get-FFmpeg {
    $paths = @(
        "ffmpeg.exe",
        "$env:ProgramFiles\ffmpeg\bin\ffmpeg.exe",
        "${env:ProgramFiles(x86)}\ffmpeg\bin\ffmpeg.exe",
        "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\*\ffmpeg.exe"
    )
    foreach ($p in $paths) {
        $found = Get-Command $p -ErrorAction SilentlyContinue
        if ($found) { return $found.Source }
    }
    return $null
}

function Get-AudioDevices {
    $devices = @()
    $devices += @{Name="VB-Cable Output (CABLE Output)"; Desc="Virtual audio cable - capture music routed through VB-Cable"}
    $devices += @{Name="Stereo Mix (Realtek High Definition Audio)"; Desc="Onboard stereo mix (may need enabling)"}
    $devices += @{Name="Stereo Mix (Realtek(R) Audio)"; Desc="Onboard stereo mix (may need enabling)"}
    $devices += @{Name="Microphone Array (Realtek)"; Desc="Microphone (not recommended for music)"}
    return $devices
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Music Push - US to VPS Music Channel" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ffmpeg = Get-FFmpeg
if (-not $ffmpeg) {
    Write-Host "[ERROR] ffmpeg not found." -ForegroundColor Red
    Write-Host "Install: winget install ffmpeg" -ForegroundColor Yellow
    Write-Host "Or download from: https://ffmpeg.org/download.html" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] ffmpeg: $ffmpeg" -ForegroundColor Green

if (-not $Device) {
    Write-Host ""
    Write-Host "Available audio capture devices (common):" -ForegroundColor Yellow
    $devices = Get-AudioDevices
    for ($i = 0; $i -lt $devices.Count; $i++) {
        Write-Host "  [$i] $($devices[$i].Name)" -ForegroundColor White
        Write-Host "      $($devices[$i].Desc)" -ForegroundColor DarkGray
    }
    Write-Host ""
    Write-Host "[*] To list ALL devices, run:" -ForegroundColor DarkGray
    Write-Host "    ffmpeg -list_devices true -f dshow -i dummy" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "[!] Recommended: Route music player -> VB-Cable Input," -ForegroundColor Yellow
    Write-Host "    then select VB-Cable Output as capture device." -ForegroundColor Yellow
    Write-Host ""
    $choice = Read-Host "Select device number (or type device name directly)"
    if ($choice -match '^\d+$' -and [int]$choice -lt $devices.Count) {
        $Device = $devices[[int]$choice].Name
    } else {
        $Device = $choice
    }
}

$envFile = Join-Path $PSScriptRoot "..\.env"
if (-not (Test-Path $envFile)) {
    Write-Host "[ERROR] .env not found. Copy .env.example from VPS and fill in values." -ForegroundColor Red
    exit 1
}

$envVars = @{}
Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
        $parts = $line.Split("=", 2)
        $envVars[$parts[0].Trim()] = $parts[1].Trim()
    }
}

$host_addr = $envVars["PUBLIC_HOST"]
$port = $envVars["SRT_PORT"]
$music_path = if ($envVars.ContainsKey("MUSIC_PATH")) { $envVars["MUSIC_PATH"] } else { "music" }
$pub_pass = $envVars["MUSIC_PUBLISH_PASSPHRASE"]

if (-not $host_addr -or -not $port -or -not $pub_pass) {
    Write-Host "[ERROR] Missing vars in .env: PUBLIC_HOST, SRT_PORT, MUSIC_PUBLISH_PASSPHRASE" -ForegroundColor Red
    exit 1
}

$srt_url = "srt://${host_addr}:${port}?streamid=publish:${music_path}&pkt_size=1316&latency=${Latency}&passphrase=${pub_pass}&pbkeylen=16"

Write-Host ""
Write-Host "Config:" -ForegroundColor Cyan
Write-Host "  Device  : $Device" -ForegroundColor White
Write-Host "  VPS     : ${host_addr}:${port}" -ForegroundColor White
Write-Host "  Path    : publish:${music_path}" -ForegroundColor White
Write-Host "  Bitrate : ${Bitrate}" -ForegroundColor White
Write-Host "  Latency : ${Latency} us ($([math]::Round($Latency/1000)) ms)" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow
Write-Host ""

try {
    & $ffmpeg -f dshow -i audio="$Device" -c:a libmp3lame -b:a $Bitrate -f mpegts $srt_url
} catch {
    Write-Host "[ERROR] FFmpeg exited: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "1. Check device name: ffmpeg -list_devices true -f dshow -i dummy" -ForegroundColor White
    Write-Host "2. Ensure Stereo Mix is enabled in Windows Sound settings -> Recording" -ForegroundColor White
    Write-Host "3. Try routing music through VB-Cable instead" -ForegroundColor White
    Write-Host "4. Verify VPS firewall allows port $port/udp" -ForegroundColor White
}
