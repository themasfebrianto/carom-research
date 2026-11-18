param(
    [string]$EnvDir = "C:\Users\omega\AppData\Local\Temp\opencode\carom-calib\env",
    [string]$Repo = (Resolve-Path "$PSScriptRoot\..\..").Path
)

$ErrorActionPreference = "Stop"
$py = Join-Path $EnvDir "Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Python env not found: $py" }
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { throw "ffmpeg not found on PATH" }

Push-Location $Repo
try {
    $out = Join-Path $Repo "out\calib-compare"
    $frames = Join-Path $out "sinkor_frames"
    New-Item -ItemType Directory -Force $out, $frames | Out-Null

    # --- frames -----------------------------------------------------------
    if (-not (Test-Path (Join-Path $out "frame_sinkor_86.png"))) {
        ffmpeg -y -loglevel error -ss 0.2 -i "clips\cawang_086_sinkor.mp4" -frames:v 1 (Join-Path $out "frame_sinkor_86.png")
    }
    if (-not (Test-Path (Join-Path $out "frame_tema_247.png"))) {
        ffmpeg -y -loglevel error -ss 0.2 -i "clips\cawang_247_20ft-tema.mp4" -frames:v 1 (Join-Path $out "frame_tema_247.png")
    }
    foreach ($t in @(0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5)) {
        $name = "frame_{0:000}.png" -f [int]($t * 10)
        $target = Join-Path $frames $name
        if (-not (Test-Path $target)) {
            ffmpeg -y -loglevel error -ss $t -i "clips\cawang_086_sinkor.mp4" -frames:v 1 $target
        }
    }

    # --- GeoCalib --------------------------------------------------------
    & $py "scripts\calib_compare\run_geocalib.py" "frames\median2.png" --out (Join-Path $out "geocalib_median2.json")
    & $py "scripts\calib_compare\run_geocalib.py" "frames\median.png" --out (Join-Path $out "geocalib_median.json")
    & $py "scripts\calib_compare\run_geocalib.py" (Join-Path $out "frame_sinkor_86.png") --out (Join-Path $out "geocalib_sinkor_86.json")
    & $py "scripts\calib_compare\run_geocalib.py" (Join-Path $out "frame_tema_247.png") --out (Join-Path $out "geocalib_tema_247.json")
    & $py "scripts\calib_compare\run_geocalib.py" "frames\median2.png" --prior-focal 1082.58 --out (Join-Path $out "geocalib_median2_prior_f1082.json")
    & $py "scripts\calib_compare\run_geocalib.py" (Join-Path $out "frame_sinkor_86.png") --prior-focal 1082.58 --out (Join-Path $out "geocalib_sinkor_prior_f1082.json")
    & $py "scripts\calib_compare\run_geocalib.py" "frames\median2.png" --weights distorted --camera-model simple_radial --out (Join-Path $out "geocalib_distorted_simple_radial_median2.json")
    & $py "scripts\calib_compare\run_geocalib_multi.py" $frames --out (Join-Path $out "geocalib_multi_sinkor.json")

    # --- AnyCalib --------------------------------------------------------
    & $py "scripts\calib_compare\run_anycalib.py" "frames\median2.png" --model-id anycalib_pinhole --cam-id simple_pinhole --out (Join-Path $out "anycalib_simple_pinhole.json")
    & $py "scripts\calib_compare\run_anycalib.py" "frames\median2.png" --model-id anycalib_pinhole --cam-id pinhole --out (Join-Path $out "anycalib_pinhole.json")
    & $py "scripts\calib_compare\run_anycalib.py" "frames\median2.png" --model-id anycalib_gen --cam-id radial:1 --out (Join-Path $out "anycalib_radial1.json")
    & $py "scripts\calib_compare\run_anycalib.py" (Join-Path $out "frame_sinkor_86.png") --model-id anycalib_pinhole --cam-id simple_pinhole --out (Join-Path $out "anycalib_simple_sinkor_86.json")
    & $py "scripts\calib_compare\run_anycalib.py" (Join-Path $out "frame_tema_247.png") --model-id anycalib_pinhole --cam-id simple_pinhole --out (Join-Path $out "anycalib_simple_tema_247.json")
    & $py "scripts\calib_compare\run_anycalib.py" "frames\median2.png" --model-id anycalib_gen --cam-id simple_pinhole --out (Join-Path $out "anycalib_gen_simple_median2.json")
    & $py "scripts\calib_compare\run_anycalib.py" (Join-Path $out "frame_tema_247.png") --model-id anycalib_gen --cam-id simple_pinhole --out (Join-Path $out "anycalib_gen_simple_tema_247.json")

    # --- fitting + summary ----------------------------------------------
    node "scripts\calib_compare\fit_compare.mjs" $Repo
    & $py "scripts\calib_compare\make_summary.py"
}
finally {
    Pop-Location
}
