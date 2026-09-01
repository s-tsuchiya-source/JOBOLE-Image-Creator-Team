param(
    [string]$InstallRoot = "$env:LOCALAPPDATA\JOBOLE-Image-Creator-Team\openvino-model-server",
    [string]$ModelsRoot = "$env:LOCALAPPDATA\JOBOLE-Image-Creator-Team\openvino-models",
    [ValidateSet("GPU", "CPU")]
    [string]$Device = "GPU",
    [int]$Port = 8000,
    [string]$Model = "OpenVINO/stable-diffusion-v1-5-int8-ov"
)

$ErrorActionPreference = "Stop"
$Setup = Join-Path $InstallRoot "ovms\setupvars.ps1"

if (-not (Test-Path $Setup)) {
    $Found = Get-ChildItem -Path $InstallRoot -Filter setupvars.ps1 -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($Found) {
        $Setup = $Found.FullName
    } else {
        throw "OpenVINO Model Server is not installed. Run .\scripts\setup_openvino_image.ps1 first."
    }
}

Write-Host "Loading OpenVINO Model Server environment..."
. $Setup

$OvmsCommand = Get-Command ovms.exe -ErrorAction SilentlyContinue
if (-not $OvmsCommand) {
    $OvmsCommand = Get-Command ovms -ErrorAction SilentlyContinue
}
if (-not $OvmsCommand) {
    $FoundExe = Get-ChildItem -Path $InstallRoot -Filter ovms.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $FoundExe) {
        throw "ovms.exe was not found after running setupvars.ps1."
    }
    $OvmsPath = $FoundExe.FullName
} else {
    $OvmsPath = $OvmsCommand.Source
}

New-Item -ItemType Directory -Force -Path $ModelsRoot | Out-Null

Write-Host ""
Write-Host "Starting local OpenVINO image generation server"
Write-Host "Device: $Device"
Write-Host "Model: $Model"
Write-Host "ModelsRoot: $ModelsRoot"
Write-Host "Endpoint: http://127.0.0.1:$Port/v3/images/generations"
Write-Host ""
Write-Host "The first run may download the model and can take time."
Write-Host "Keep this PowerShell window open while JOBOLE generates images."
Write-Host "Stop the server with Ctrl+C."
Write-Host ""

& $OvmsPath `
    --rest_port $Port `
    --model_repository_path $ModelsRoot `
    --task image_generation `
    --source_model $Model `
    --target_device $Device

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "OVMS exited with code $LASTEXITCODE."
    if ($Device -eq "GPU") {
        Write-Host "If Intel GPU memory/driver initialization failed, try:"
        Write-Host ".\scripts\start_openvino_image.ps1 -Device CPU"
    }
    exit $LASTEXITCODE
}
