param(
    [string]$ArchivePath = "data/raw/a2d2-preview.tar",
    [string]$Sequence = "20190401_121727",
    [string]$Camera = "cam_front_right",
    [int]$FrameCount = 20,
    [string]$OutputDir = "data/raw/a2d2-subset"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $ArchivePath)) {
    throw "Archive not found: $ArchivePath"
}

$entries = tar -tf $ArchivePath

$cameraPrefix = "camera_lidar/$Sequence/camera/$Camera/"
$matchingPngs = $entries | Where-Object { $_ -like "$cameraPrefix*.png" } | Sort-Object

if (-not $matchingPngs -or $matchingPngs.Count -eq 0) {
    throw "No PNG frames found for sequence '$Sequence' and camera '$Camera'."
}

$selectedPngs = $matchingPngs | Select-Object -First $FrameCount
$selectedBases = $selectedPngs | ForEach-Object { [System.IO.Path]::GetFileNameWithoutExtension($_) }

$selectedEntries = New-Object System.Collections.Generic.List[string]

foreach ($entry in $selectedPngs) {
    $selectedEntries.Add($entry)
}

foreach ($base in $selectedBases) {
    $jsonPath = "$cameraPrefix$base.json"
    if ($entries -contains $jsonPath) {
        $selectedEntries.Add($jsonPath)
    }
}

$busSignals = "camera_lidar/$Sequence/bus_signals_${Sequence}.json"
if ($entries -contains $busSignals) {
    $selectedEntries.Add($busSignals)
}

New-Item -ItemType Directory -Force $OutputDir | Out-Null

$tempList = Join-Path $env:TEMP "a2d2_subset_entries.txt"
$selectedEntries | Set-Content -Path $tempList -Encoding ascii

tar -xf $ArchivePath -C $OutputDir -T $tempList

Remove-Item $tempList -ErrorAction SilentlyContinue

Write-Host "Extracted $($selectedPngs.Count) frames for $Camera from sequence $Sequence into $OutputDir"
