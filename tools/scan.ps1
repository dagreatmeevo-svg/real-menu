<#
.SYNOPSIS
  Photos (or a video) of one dish part -> textured GLB, using COLMAP + OpenMVS on the GPU.

.EXAMPLE
  .\tools\scan.ps1 -Photos D:\shoot\patty -Name patty
  .\tools\scan.ps1 -Video D:\shoot\patty.mp4 -Name patty
  .\tools\scan.ps1 -Photos D:\shoot\patty -Name patty -Quality high

  Result: scans\patty\patty.glb  (open it in Blender for cleanup, see PIPELINE.md)
#>
param(
  [string]$Photos,
  [string]$Video,
  [Parameter(Mandatory = $true)][string]$Name,
  [ValidateSet('fast', 'normal', 'high')][string]$Quality = 'normal',
  [int]$Fps = 3,
  [string]$Colmap = 'C:\tools\colmap\COLMAP.bat',
  [string]$OpenMVS = 'C:\tools\openmvs_cuda',
  [string]$Blender = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
)
$ErrorActionPreference = 'Stop'

function Step($msg) { Write-Host "`n=== $msg" -ForegroundColor Cyan }
function Run($exe, [string[]]$argv) {
  # COLMAP logs to stderr; in Windows PowerShell that must not count as an error
  $ErrorActionPreference = 'Continue'
  & $exe @argv 2>&1 | ForEach-Object { "$_" }
  if ($LASTEXITCODE -ne 0) { throw "$([IO.Path]::GetFileName($exe)) failed (exit $LASTEXITCODE). See the log above or *.log in $work" }
}

if (-not $Photos -and -not $Video) { throw 'Give -Photos <folder> or -Video <file>.' }
if (-not (Test-Path $Colmap)) { throw "COLMAP not found at $Colmap" }
if (-not (Test-Path "$OpenMVS\DensifyPointCloud.exe")) { throw "OpenMVS not found at $OpenMVS" }
if (-not (Test-Path $Blender)) { throw "Blender not found at $Blender" }
if ($Name -notmatch '^[a-z0-9_-]+$') { throw 'Name must be lowercase letters, numbers, - or _ (e.g. patty, bun_top).' }

# quality presets: image size used for matching / dense, and mesh face budget
$q = @{
  fast   = @{ feat = 2000; dense = 1600; faces = 80000;  refine = $false }
  normal = @{ feat = 3200; dense = 2400; faces = 150000; refine = $false }
  high   = @{ feat = 4000; dense = 3200; faces = 300000; refine = $true }
}[$Quality]

$root = Split-Path -Parent $PSScriptRoot
$work = Join-Path $root "scans\$Name"
$images = Join-Path $work 'images'
New-Item -ItemType Directory -Force $images | Out-Null
$sw = [Diagnostics.Stopwatch]::StartNew()

Step "1/7 Collect images -> $images"
if ($Video) {
  if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { throw 'ffmpeg is needed for -Video.' }
  & ffmpeg -hide_banner -loglevel error -y -i $Video -vf "fps=$Fps" -q:v 2 (Join-Path $images 'f_%04d.jpg')
  if ($LASTEXITCODE -ne 0) { throw 'ffmpeg failed to extract frames.' }
} else {
  Get-ChildItem $Photos -File | Where-Object { $_.Extension -match '^\.(jpe?g|png|tiff?)$' } |
    Copy-Item -Destination $images
}
$count = (Get-ChildItem $images -File).Count
Write-Host "$count images"
if ($count -lt 20) { throw "Only $count images. Shoot at least 50 (70-150 is best)." }

$db = Join-Path $work 'database.db'
$sparse = Join-Path $work 'sparse'
$dense = Join-Path $work 'dense'
if (Test-Path $db) { Remove-Item $db }
New-Item -ItemType Directory -Force $sparse | Out-Null

Step '2/7 Find features (GPU)'
Run $Colmap @('feature_extractor', '--database_path', $db, '--image_path', $images,
  '--ImageReader.single_camera', '1', '--ImageReader.camera_model', 'OPENCV',
  '--FeatureExtraction.use_gpu', '1', '--FeatureExtraction.max_image_size', "$($q.feat)")

Step '3/7 Match photos (GPU)'
$matcher = if ($Video) { 'sequential_matcher' } else { 'exhaustive_matcher' }
Run $Colmap @($matcher, '--database_path', $db, '--FeatureMatching.use_gpu', '1')

Step '4/7 Solve camera positions'
Run $Colmap @('mapper', '--database_path', $db, '--image_path', $images, '--output_path', $sparse)
# COLMAP may split into several models; keep the one with the most cameras
$best = Get-ChildItem $sparse -Directory | Sort-Object { (Get-Item (Join-Path $_.FullName 'images.bin')).Length } -Descending | Select-Object -First 1
if (-not $best) { throw 'No camera solution. Photos need more overlap, sharper focus or more surface texture.' }
Write-Host "using model $($best.Name)"

Step '5/7 Undistort images'
if (Test-Path $dense) { Remove-Item $dense -Recurse -Force }
Run $Colmap @('image_undistorter', '--image_path', $images, '--input_path', $best.FullName,
  '--output_path', $dense, '--output_type', 'COLMAP', '--max_image_size', "$($q.dense)")

Step '6/7 Dense cloud and mesh (OpenMVS, GPU)'
Push-Location $work
try {
  Run "$OpenMVS\InterfaceCOLMAP.exe" @('-i', $dense, '-o', 'scene.mvs', '--image-folder', (Join-Path $dense 'images'))
  Run "$OpenMVS\DensifyPointCloud.exe" @('scene.mvs', '-o', 'scene_dense.mvs')
  Run "$OpenMVS\ReconstructMesh.exe" @('scene_dense.mvs', '-p', 'scene_dense.ply', '-o', 'scene_mesh.ply',
    '--target-face-num', "$($q.faces)")
  $mesh = 'scene_mesh.ply'
  if ($q.refine) {
    Run "$OpenMVS\RefineMesh.exe" @('scene_dense.mvs', '-m', $mesh, '-o', 'scene_refined.ply', '--resolution-level', '1')
    $mesh = 'scene_refined.ply'
  }

  Step '7/7 Texture -> GLB'
  # Seam leveling is off: in OpenMVS 2.4 it paints large parts of the texture black.
  # Its own GLB export also mismatches the texture, so export OBJ and convert in Blender.
  Run "$OpenMVS\TextureMesh.exe" @('scene_dense.mvs', '-m', $mesh, '-o', "$Name-openmvs.obj",
    '--export-type', 'obj', '--max-texture-size', '4096',
    '--global-seam-leveling', '0', '--local-seam-leveling', '0')
  Run $Blender @('--background', '--python', (Join-Path $PSScriptRoot 'obj_to_glb.py'), '--',
    (Join-Path $work "$Name-openmvs.obj"), (Join-Path $work "$Name.glb"))
} finally { Pop-Location }

$glb = Join-Path $work "$Name.glb"
if (-not (Test-Path $glb)) { throw "TextureMesh finished but $glb is missing." }
$mb = [math]::Round((Get-Item $glb).Length / 1MB, 1)
Write-Host "`nDone in $([math]::Round($sw.Elapsed.TotalMinutes,1)) min: $glb ($mb MB)" -ForegroundColor Green
Write-Host 'Next: import it in Blender, clean, scale, name the layer (PIPELINE.md step 3).'
