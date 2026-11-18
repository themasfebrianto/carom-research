#!/usr/bin/env python
"""Extract one frame per timestamp from a video (or a folder of videos).

Example:
  py scripts/i24_frames.py "recording cawang.mp4" --out out/i24/frames_smoke --times 10 30 50
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def extract(video: Path, out_dir: Path, times: list[float], prefix: str | None) -> list[Path]:
    stem = prefix or video.stem
    made = []
    for t in times:
        label = f"{t:06.1f}".replace(".", "_")
        dst = out_dir / f"{stem}_{label}.png"
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-ss", f"{t:.3f}", "-i", str(video),
            "-frames:v", "1", "-y", str(dst),
        ]
        subprocess.run(cmd, check=True)
        if dst.exists() and dst.stat().st_size > 0:
            made.append(dst)
            print(f"{video.name} @ {t:g}s -> {dst} ({dst.stat().st_size//1024} KB)")
    return made


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="video file or directory")
    ap.add_argument("--out", required=True)
    ap.add_argument("--times", nargs="+", type=float, default=[10.0, 30.0, 50.0])
    ap.add_argument("--prefix", default=None)
    args = ap.parse_args()

    src = Path(args.input)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if src.is_dir():
        videos = sorted(list(src.rglob("*.mp4")) + list(src.rglob("*.mkv")))
    else:
        videos = [src]

    if not videos:
        raise SystemExit(f"no video found under {src}")

    total = 0
    for video in videos:
        prefix = None
        if src.is_dir():
            prefix = "_".join(video.with_suffix("").parts[-3:])
        total += len(extract(video, out_dir, args.times, prefix))
    print(f"\n{total} frame(s) -> {out_dir}")


if __name__ == "__main__":
    main()
