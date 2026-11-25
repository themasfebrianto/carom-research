#!/usr/bin/env python
"""One-command CenterLoc3D training on SVLD-3D for Google Colab.

Handles everything a fresh Colab VM needs: GPU guard, dependencies, cloning and
patching CenterLoc3D, downloading/extracting the SVLD archives from Drive,
building the annotation txt files, and launching the training loop with
checkpoints on Drive.

Typical use inside a Colab cell:

    !python scripts/colab_train_centerloc3d.py --preset smoke   # ~15 min
    !python scripts/colab_train_centerloc3d.py --preset full    # real run

Presets
    smoke  A-C archive, 200 train images, 2 epochs, batch 4, output /content/out
    full   all archives, 50 epochs, batch 8, output on Drive when mounted

Everything is resumable: rerunning `--preset full` continues from
`<out>/checkpoint_last.pth` when it exists.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tarfile
import time
import zipfile
from pathlib import Path

CENTERLOC_REPO = "https://github.com/stjuliet/CenterLoc3D.git"

# Public SVLD-3D archives on Google Drive (.rar, RAR5). Third value is the
# number of images the archive should contain, used to verify extraction.
ARCHIVES = {
    "ac": [("A-C", "1yO9av6qtLxOehT-vRivaX_WX6TT-jIvc", 7043)],
    "all": [
        ("A-C", "1yO9av6qtLxOehT-vRivaX_WX6TT-jIvc", 7043),
        ("D", "13i341cnFtNVlRvVBjSAmUGtxEiHt_Fjz", 3848),
        ("E", "1Z-lv_NQtBc8EFYJaFapF69H79m2Ce2mO", 3701),
    ],
}

PRESETS = {
    "smoke": dict(data="ac", max_images=200, epochs=2, batch=4, freeze_epochs=1),
    "full": dict(data="all", max_images=0, epochs=50, batch=8, freeze_epochs=5),
}

DRIVE_OUT = "/content/drive/MyDrive/centerloc3d"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    log("$ " + " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, check=True, **kwargs)


def ensure_gpu(allow_cpu: bool = False) -> None:
    import torch

    if not torch.cuda.is_available():
        if allow_cpu:
            log("CUDA tidak ada; lanjut di CPU karena --allow-cpu (hanya untuk uji)")
            return
        raise SystemExit(
            "GPU tidak tersedia. Di Colab: Runtime > Change runtime type > "
            "Hardware accelerator = L4 (atau T4), lalu jalankan ulang sel ini."
        )
    props = torch.cuda.get_device_properties(0)
    log(
        f"GPU: {props.name} {props.total_memory / 1024**3:.1f} GiB, "
        f"torch {torch.__version__}, cuda {torch.version.cuda}"
    )


def ensure_deps() -> None:
    import importlib

    missing = []
    for mod, pkg in [
        ("gdown", "gdown"),
        ("cv2", "opencv-python-headless"),
        ("tensorboardX", "tensorboardX"),
    ]:
        try:
            importlib.import_module(mod)
        except Exception:
            missing.append(pkg)
    if missing:
        run([sys.executable, "-m", "pip", "install", "-q", *missing])

    # RAR5 extractors for the SVLD archives. Installed one by one so a missing
    # package name cannot cancel the others; every extractor is optional.
    if shutil.which("apt-get"):
        subprocess.run("apt-get -qq update >/dev/null 2>&1", shell=True, check=False)
        for pkg in ("p7zip-full", "unar", "libarchive-tools", "unrar-free", "unrar"):
            subprocess.run(
                f"DEBIAN_FRONTEND=noninteractive apt-get -qq install -y {pkg} >/dev/null 2>&1",
                shell=True,
                check=False,
            )


def ensure_repo(repo: Path) -> None:
    if (repo / "train" / "train.py").exists():
        log(f"repo sudah ada: {repo}")
        return
    if repo.exists():
        shutil.rmtree(repo, ignore_errors=True)
    run(["git", "clone", "--depth", "1", CENTERLOC_REPO, str(repo)])


def patch_repo(repo: Path, here: Path) -> None:
    run([sys.executable, str(here / "patch_centerloc3d.py"), "--repo", str(repo)])


def download(url_id: str, dest: Path) -> Path:
    """Download one public Drive file, retrying on transient/quota errors."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 100 * 1024 * 1024:
        log(f"sudah terunduh: {dest} ({dest.stat().st_size / 1024**3:.2f} GB)")
        return dest

    tmp = dest.with_name(dest.name + ".part")
    last = None
    for attempt in range(1, 4):
        tmp.unlink(missing_ok=True)
        try:
            run(
                [sys.executable, "-m", "gdown", url_id, "-O", str(tmp), "--quiet"],
                timeout=3600,
            )
            if tmp.exists() and tmp.stat().st_size > 0:
                tmp.replace(dest)
                log(f"terunduh {dest.name}: {dest.stat().st_size / 1024**3:.2f} GB")
                return dest
        except subprocess.CalledProcessError as exc:
            last = exc
        except subprocess.TimeoutExpired as exc:
            last = exc
        log(f"unduh gagal (percobaan {attempt}/3), ulangi 20 s lagi")
        time.sleep(20)
    raise SystemExit(
        f"gagal mengunduh {url_id}: {last}. Kalau pesannya soal kuota Drive, "
        "coba lagi beberapa jam kemudian atau unduh manual lalu taruh di "
        f"{dest.parent}."
    )


def extract(archive: Path, out_dir: Path, expected_images: int) -> int:
    """Extract one archive and verify that the image count is plausible.

    The SVLD archives are RAR5; older p7zip builds can fail or extract only
    part of a RAR5 file without a clear error, so each extractor is tried and
    the result is counted before it is accepted.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    if archive.suffix.lower() == ".zip":
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(out_dir)
        return count_images(out_dir)

    cmds = [
        ["unar", "-q", "-f", "-o", str(out_dir), str(archive)],
        ["7z", "x", "-y", f"-o{out_dir}", str(archive)],
        ["bsdtar", "-xf", str(archive), "-C", str(out_dir)],
        ["unrar", "x", "-o+", "-idq", str(archive), str(out_dir)],
    ]
    floor = int(expected_images * 0.9)
    for cmd in cmds:
        if shutil.which(cmd[0]) is None:
            continue
        log("extract: " + " ".join(cmd))
        res = subprocess.run(cmd, capture_output=True, text=True)
        n_img = count_images(out_dir)
        n_xml = count_files(out_dir, (".xml",))
        if n_img >= floor and n_xml >= floor:
            log(f"  {cmd[0]}: {n_img} gambar, {n_xml} xml")
            return n_img
        detail = (res.stderr or res.stdout or "").strip()[:300]
        log(
            f"  {cmd[0]} tidak memadai: {n_img} gambar / {n_xml} xml "
            f"(butuh >= {floor}). {detail}"
        )
    raise SystemExit(
        f"gagal mengekstrak {archive.name} (butuh >= {floor} gambar dan xml). "
        "Coba `apt-get install -y unar` lalu jalankan ulang."
    )


def count_files(root: Path, suffixes: tuple[str, ...]) -> int:
    return sum(1 for p in root.rglob("*") if p.suffix.lower() in suffixes)


def count_images(root: Path) -> int:
    return count_files(root, (".jpg", ".jpeg", ".png"))


def find_data2021(root: Path) -> list[Path]:
    return [p for p in root.rglob("DATA2021") if p.is_dir()]


def merge_archives(raw_dir: Path, merged: Path) -> None:
    merged.mkdir(parents=True, exist_ok=True)
    found = find_data2021(raw_dir)
    if not found:
        raise SystemExit(f"tidak menemukan folder DATA2021 di {raw_dir}")
    for src in found:
        log(f"merge {src}")
        for sub in ("JPEGImages", "Annotations", "Calib"):
            s = src / sub
            if not s.is_dir():
                continue
            shutil.copytree(s, merged / sub, dirs_exist_ok=True)
        if not (merged / "ImageSets").exists() and (src / "ImageSets").is_dir():
            shutil.copytree(src / "ImageSets", merged / "ImageSets", dirs_exist_ok=True)

    n_img = len(list((merged / "JPEGImages").glob("*")))
    log(f"data gabungan: {n_img} gambar di {merged}")


def build_txt(merged: Path, dataset_dir: Path, here: Path, name: str) -> tuple[Path, Path]:
    run(
        [
            sys.executable,
            str(here / "make_centerloc3d_txt.py"),
            "--data-root", str(merged),
            "--out-dir", str(dataset_dir),
            "--out-name", name,
            "--splits", "train,val",
        ]
    )
    return dataset_dir / f"{name}_train.txt", dataset_dir / f"{name}_val.txt"


def subsample(txt: Path, limit: int, out: Path) -> Path:
    lines = [ln for ln in txt.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if limit and len(lines) > limit:
        step = max(1, len(lines) // limit)
        lines = lines[::step][:limit]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"{out.name}: {len(lines)} baris")
    return out


def maybe_restore_tar(cache: Path, merged: Path) -> bool:
    if not cache.is_file():
        return False
    log(f"restore data dari cache {cache}")
    merged.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(cache) as tf:
        tf.extractall(merged.parent)
    return True


def maybe_write_tar(cache: Path, merged: Path) -> None:
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        log(f"menyimpan cache data ke {cache} (beberapa menit)")
        with tarfile.open(cache, "w") as tf:
            tf.add(merged, arcname=merged.name)
        log("cache tersimpan")
    except Exception as exc:  # pragma: no cover - disk/quota issues only
        log(f"gagal menyimpan cache: {exc}")


def script_rev(here: Path) -> str:
    """Short git revision of the scripts, so logs show which code ran."""
    try:
        res = subprocess.run(
            ["git", "-C", str(here.parent), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        rev = res.stdout.strip()
        return rev or "unknown"
    except Exception:
        return "unknown"


def main() -> None:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser("CenterLoc3D on SVLD-3D (Colab)")
    ap.add_argument("--preset", choices=sorted(PRESETS), default="smoke")
    ap.add_argument("--data", choices=["ac", "all", "none"], default=None)
    ap.add_argument("--max-images", type=int, default=None)
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--batch", type=int, default=None)
    ap.add_argument("--freeze-epochs", type=int, default=None)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--num-workers", type=int, default=4)
    ap.add_argument("--repo", default="/content/CenterLoc3D")
    ap.add_argument("--work", default="/content/work")
    ap.add_argument("--out", default="")
    ap.add_argument("--data-root", default="", help="DATA2021 yang sudah ada; lewati unduh/ekstrak")
    ap.add_argument("--allow-cpu", action="store_true", help="uji lokal tanpa CUDA")
    ap.add_argument("--cache-tar", default="", help="tar data di Drive untuk sesi berikutnya")
    ap.add_argument("--resume", default="auto", help="auto, none, atau path checkpoint")
    ap.add_argument("--skip-data", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    preset = PRESETS[args.preset]
    data_mode = args.data or preset["data"]
    max_images = preset["max_images"] if args.max_images is None else args.max_images
    epochs = preset["epochs"] if args.epochs is None else args.epochs
    batch = preset["batch"] if args.batch is None else args.batch
    freeze_epochs = (
        preset["freeze_epochs"] if args.freeze_epochs is None else args.freeze_epochs
    )

    drive_mounted = Path("/content/drive/MyDrive").is_dir()
    out = Path(args.out) if args.out else Path(DRIVE_OUT if drive_mounted else "/content/out")
    work = Path(args.work)
    repo = Path(args.repo)
    merged = work / "svld" / "DATA2021"
    raw = work / "raw"

    log(f"preset={args.preset} data={data_mode} epochs={epochs} batch={batch}")
    log(f"scripts rev={script_rev(here)}")
    log(f"out={out} (drive_mounted={drive_mounted})")

    ensure_gpu(args.allow_cpu)
    ensure_deps()
    ensure_repo(repo)
    patch_repo(repo, here)

    if args.data_root:
        merged = Path(args.data_root)
        log(f"pakai data lokal: {merged}")

    if not args.data_root and not args.skip_data and data_mode != "none":
        cache = Path(args.cache_tar) if args.cache_tar else None
        restored = bool(cache and maybe_restore_tar(cache, merged))
        if not restored:
            if merged.is_dir() and any((merged / "JPEGImages").glob("*")):
                log(f"pakai data yang sudah ada: {merged}")
            else:
                for name, file_id, expected in ARCHIVES[data_mode]:
                    dest = raw / f"SVLD-{name}.rar"
                    download(file_id, dest)
                    extract(dest, raw / name, expected)
                merge_archives(raw, merged)
                if cache:
                    maybe_write_tar(cache, merged)
            # free disk: archives and per-scene trees are no longer needed
            shutil.rmtree(raw, ignore_errors=True)

    train_txt, val_txt = build_txt(merged, repo / "dataset", here, f"DATA2021_{args.preset}")
    if max_images:
        train_txt = subsample(train_txt, max_images, train_txt.with_name(train_txt.stem + "_sub.txt"))
        val_txt = subsample(val_txt, max(20, max_images // 5), val_txt.with_name(val_txt.stem + "_sub.txt"))

    resume = ""
    if args.resume == "auto":
        cand = out / "checkpoint_last.pth"
        resume = str(cand) if cand.exists() else ""
    elif args.resume != "none":
        resume = args.resume
    if resume:
        log(f"resume dari {resume}")

    cmd = [
        sys.executable, str(here / "train_centerloc3d_colab.py"),
        "--repo", str(repo),
        "--train-txt", str(train_txt),
        "--val-txt", str(val_txt),
        "--epochs", str(epochs),
        "--freeze-epochs", str(freeze_epochs),
        "--batch", str(batch),
        "--lr", str(args.lr),
        "--num-workers", str(args.num_workers),
        "--out", str(out),
        "--amp",
    ]
    if resume:
        cmd += ["--resume", resume]
    if args.dry_run:
        cmd += ["--max-iters", "2"]

    log("mulai training")
    run(cmd)


if __name__ == "__main__":
    main()
