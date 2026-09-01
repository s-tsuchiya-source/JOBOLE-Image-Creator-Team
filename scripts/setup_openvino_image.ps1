param(
    [string]$InstallRoot = "$env:LOCALAPPDATA\JOBOLE-Image-Creator-Team\openvino-model-server"
)

$ErrorActionPreference = "Stop"
$ReleaseTag = "v2026.3"
$Version = "2026.3.0"
$ArchiveName = "ovms_windows_${Version}_python_off.zip"
$DownloadUrl = "https://github.com/openvinotoolkit/model_server/releases/download/$ReleaseTag/$ArchiveName"
$ArchivePath = Join-Path $env:TEMP $ArchiveName
$ExpectedSetup = Join-Path $InstallRoot "ovms\setupvars.ps1"

Write-Host "OpenVINO Model Server setup"
Write-Host "InstallRoot: $InstallRoot"

if (Test-Path $ExpectedSetup) {
    Write-Host "OVMS is already installed: $ExpectedSetup"
    Write-Host "Next: .\scripts\start_openvino_image.ps1"
    exit 0
}

New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null

Write-Host "Downloading official OpenVINO Model Server package..."
Write-Host $DownloadUrl
Invoke-WebRequest -Uri $DownloadUrl -OutFile $ArchivePath

Write-Host "Extracting..."
Expand-Archive -Path $ArchivePath -DestinationPath $InstallRoot -Force
Remove-Item $ArchivePath -Force -ErrorAction SilentlyContinue

if (-not (Test-Path $ExpectedSetup)) {
    $Found = Get-ChildItem -Path $InstallRoot -Filter setupvars.ps1 -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($Found) {
        Write-Host "OVMS extracted. setupvars found at: $($Found.FullName)"
    } else {
        throw "OVMS extraction completed but setupvars.ps1 was not found under $InstallRoot"
    }
}

Write-Host ""
Write-Host "OPENVINO SETUP: PASS"
Write-Host "Microsoft Visual C++ Redistributable is required by the official Windows package."
Write-Host "If the server fails to start with a missing runtime DLL, install/update Microsoft Visual C++ Redistributable."
Write-Host ""
Write-Host "Next command:"
Write-Host ".\scripts\start_openvino_image.ps1"
