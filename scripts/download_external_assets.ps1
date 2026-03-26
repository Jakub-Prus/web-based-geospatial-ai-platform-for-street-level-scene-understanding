param(
    [switch]$DownloadA2D2Preview
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$rawDir = Join-Path $repoRoot "data\\raw"
$modelDir = Join-Path $rawDir "models"

$yolo11nUrl = "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo11n.pt"
$midasTinyUrl = "https://github.com/isl-org/MiDaS/releases/download/v3_1/dpt_swin2_tiny_256.pt"
$a2d2PreviewUrl = "https://aev-autonomous-driving-dataset.s3.eu-central-1.amazonaws.com/a2d2-preview.tar"

New-Item -ItemType Directory -Force $rawDir | Out-Null
New-Item -ItemType Directory -Force $modelDir | Out-Null

function Download-IfMissing {
    param(
        [string]$Url,
        [string]$OutputPath
    )

    if (Test-Path $OutputPath) {
        Write-Host "Skipping existing file: $OutputPath"
        return
    }

    Write-Host "Downloading $Url"
    curl.exe -L $Url -o $OutputPath
}

Download-IfMissing -Url $yolo11nUrl -OutputPath (Join-Path $modelDir "yolo11n.pt")
Download-IfMissing -Url $midasTinyUrl -OutputPath (Join-Path $modelDir "dpt_swin2_tiny_256.pt")

if ($DownloadA2D2Preview) {
    Download-IfMissing -Url $a2d2PreviewUrl -OutputPath (Join-Path $rawDir "a2d2-preview.tar")
} else {
    Write-Host "Skipping A2D2 preview tar. Re-run with -DownloadA2D2Preview to fetch the 4.63 GB preview archive."
}
