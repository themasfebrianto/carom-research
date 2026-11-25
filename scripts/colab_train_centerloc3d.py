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
import json
import shutil
import subprocess
import sys
import tarfile
import time
import zipfile
from pathlib import Path

CENTERLOC_REPO = "https://github.com/stjuliet/CenterLoc3D.git"

# Written into the merged dataset once extraction has been verified.  The
# archive itself contains empty XMLs, so "every image has a non-empty XML" is
# not the right test after the first successful extraction.  Bump the version
# when the extraction/repair logic changes, so old markers are distrusted.
MARKER = ".extraction.json"
MARKER_VERSION = 2

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
    """Extract one archive and make sure the annotations are usable.

    The SVLD archives are RAR5.  In practice `unar` on Colab extracts every
    image but leaves a subset of the XML files empty (0 bytes).  So:
      1. try each extractor until nearly all images are present;
      2. if many XMLs are empty, re-extract just the Annotations folder with
         the other tools (cheap, annotations are small);
      3. if a tool still leaves empty XMLs, let the next tool overwrite them.
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
    xml_ok = 0.95

    n_img = count_images(out_dir)
    if n_img >= floor and count_xml(out_dir) >= int(n_img * xml_ok):
        log(f"pakai hasil ekstraksi yang ada: {n_img} gambar")
        return n_img

    for cmd in cmds:
        if shutil.which(cmd[0]) is None:
            continue
        if count_images(out_dir) < floor:
            shutil.rmtree(out_dir, ignore_errors=True)
            out_dir.mkdir(parents=True, exist_ok=True)
        log("extract: " + " ".join(cmd))
        res = subprocess.run(cmd, capture_output=True, text=True)
        n_img = count_images(out_dir)
        if n_img < floor:
            detail = (res.stderr or res.stdout or "").strip()[:300]
            log(f"  {cmd[0]} tidak memadai: {n_img}/{expected_images} gambar. {detail}")
            continue
        n_xml = count_xml(out_dir)
        if n_xml >= int(n_img * xml_ok):
            log(f"  {cmd[0]}: {n_img} gambar, {n_xml} xml valid")
            return n_img
        log(f"  {cmd[0]}: {n_img} gambar, hanya {n_xml} xml valid; perbaiki Annotations")
        n_xml = reextract_annotations(archive, out_dir)
        log(f"  setelah perbaikan: {n_xml} xml valid")
        if n_xml >= int(n_img * xml_ok):
            return n_img
        log(f"  {cmd[0]} masih menyisakan xml kosong; coba ekstraktor lain")

    n_img = count_images(out_dir)
    if n_img >= floor:
        log(f"tidak ada ekstraktor yang bersih: {n_img} gambar, xml kosong dilewati")
        return n_img
    raise SystemExit(
        f"gagal mengekstrak {archive.name} (butuh >= {floor} gambar). "
        "Coba `apt-get install -y unar` lalu jalankan ulang."
    )


def reextract_annotations(archive: Path, out_dir: Path) -> int:
    """Re-extract only the Annotations with every tool and keep the best result.

    The XMLs are written into the real DATA2021/Annotations folder(s) under
    out_dir, not next to them, so the later merge actually sees them.
    """
    dest = out_dir / "_ann_retry"
    targets = data_dirs(out_dir) or [out_dir]
    best = count_xml(out_dir)
    cmds = [
        ["7z", "x", "-y", f"-o{dest}", str(archive), "-i!*Annotations*"],
        ["bsdtar", "-xf", str(archive), "-C", str(dest), "--include", "*Annotations*"],
        ["unrar", "x", "-o+", "-idq", str(archive), "*Annotations*", str(dest) + "/"],
    ]
    for cmd in cmds:
        if shutil.which(cmd[0]) is None:
            continue
        shutil.rmtree(dest, ignore_errors=True)
        dest.mkdir(parents=True, exist_ok=True)
        res = subprocess.run(cmd, capture_output=True, text=True)
        found = list(dest.rglob("*.xml"))
        if not found:
            detail = (res.stderr or res.stdout or "").strip()[:200]
            log(f"  {cmd[0]}: tidak menemukan xml. {detail}")
            continue
        good = 0
        for p in found:
            if p.stat().st_size <= 100:
                continue
            for target in targets:
                ann = target / "Annotations"
                ann.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, ann / p.name)
            good += 1
        total = count_xml(out_dir)
        log(f"  {cmd[0]}: {good} xml ditulis ulang, total valid {total}")
        best = max(best, total)
    shutil.rmtree(dest, ignore_errors=True)
    return best


def count_files(root: Path, suffixes: tuple[str, ...]) -> int:
    return sum(1 for p in root.rglob("*") if p.suffix.lower() in suffixes)


def count_images(root: Path) -> int:
    return count_files(root, (".jpg", ".jpeg", ".png"))


def count_xml(root: Path, min_bytes: int = 100) -> int:
    """Count non-empty XML files; 0-byte entries are the failure mode we see."""
    return sum(
        1
        for p in root.rglob("*.xml")
        if p.is_file()
        and p.stat().st_size >= min_bytes
        and "_ann_retry" not in p.parts
    )


def data_dirs(root: Path) -> list[Path]:
    """Folders that have both JPEGImages and Annotations (DATA2021 layout)."""
    dirs = {p.parent for p in root.rglob("Annotations") if p.is_dir()}
    return sorted(d for d in dirs if (d / "JPEGImages").is_dir())


def data_is_sane(merged: Path, min_ratio: float = 0.95) -> bool:
    """An image without a readable annotation cannot be trained on.

    SVLD ships one XML per image, but some XMLs in the public archives are
    genuinely empty (0 bytes).  After the first verified extraction a marker
    records how many images and valid XMLs were obtained, so later runs check
    that the folder still holds those files instead of demanding a ratio the
    source cannot reach.
    """
    if not merged.is_dir():
        return False
    n_img = count_images(merged)
    if n_img == 0:
        return False
    n_xml = count_xml(merged)
    ratio = n_xml / n_img
    marker = merged / MARKER
    if marker.is_file():
        try:
            info = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            info = {}
        want_img = int(info.get("images", 0) or 0)
        want_xml = int(info.get("xml_valid", 0) or 0)
        version = int(info.get("version", 0) or 0)
        if version != MARKER_VERSION:
            log(f"marker versi lama ({version}); data akan diekstrak ulang")
            return False
        if want_img > 0 and n_img >= want_img * 0.98 and n_xml >= want_xml * 0.98:
            log(
                f"data sudah diverifikasi: {n_img} gambar, {n_xml} xml valid "
                f"({ratio:.1%})"
            )
            return True
        log("marker ada tapi isi folder berkurang; data dianggap tidak lengkap")
        return False
    if ratio < min_ratio:
        log(f"data tidak sehat: {n_img} gambar, hanya {n_xml} xml valid ({ratio:.1%})")
        return False
    return True


def write_marker(merged: Path) -> None:
    """Record the verified counts so a rerun does not distrust a good dataset."""
    info = {
        "version": MARKER_VERSION,
        "images": count_images(merged),
        "xml_valid": count_xml(merged),
        "written": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (merged / MARKER).write_text(json.dumps(info, indent=1), encoding="utf-8")
    log(f"tandai data terverifikasi: {info['images']} gambar, {info['xml_valid']} xml valid")


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
    ap.add_argument("--resume", default=None, help="auto, none, atau path checkpoint")
    ap.add_argument("--skip-data", action="store_true")
    ap.add_argument("--refresh-data", action="store_true", help="hapus dan ekstrak ulang data")
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
    out = Path(args.out) if args.out else Path(
        "/content/out" if args.preset == "smoke"
        else (DRIVE_OUT if drive_mounted else "/content/out")
    )
    run_tag = f"{args.preset}|{data_mode}|b{batch}"
    resume_arg = args.resume
    if resume_arg is None:
        # A smoke checkpoint is a 200-image toy model; it must never leak into
        # the full run.  Full training keeps resuming across sessions.
        resume_arg = "none" if args.preset == "smoke" else "auto"
    work = Path(args.work)
    repo = Path(args.repo)
    merged = work / "svld" / "DATA2021"
    raw = work / "raw"

    log(f"preset={args.preset} data={data_mode} epochs={epochs} batch={batch}")
    log(f"scripts rev={script_rev(here)}")
    log(f"out={out} (drive_mounted={drive_mounted}) resume={resume_arg}")

    ensure_gpu(args.allow_cpu)
    ensure_deps()
    ensure_repo(repo)
    patch_repo(repo, here)

    if args.data_root:
        merged = Path(args.data_root)
        log(f"pakai data lokal: {merged}")

    if args.refresh_data and merged.is_dir():
        log("--refresh-data: menghapus data hasil ekstrak lama")
        shutil.rmtree(merged, ignore_errors=True)

    if not args.data_root and not args.skip_data and data_mode != "none":
        cache = Path(args.cache_tar) if args.cache_tar else None
        restored = bool(cache and maybe_restore_tar(cache, merged) and data_is_sane(merged))
        if not restored:
            if data_is_sane(merged):
                log(f"pakai data yang sudah ada: {merged}")
            else:
                if merged.is_dir():
                    log("data lama tidak lengkap, ekstrak ulang")
                    shutil.rmtree(merged, ignore_errors=True)
                if cache and cache.is_file():
                    log(f"cache {cache} juga tidak lengkap, hapus")
                    cache.unlink(missing_ok=True)
                for name, file_id, expected in ARCHIVES[data_mode]:
                    dest = raw / f"SVLD-{name}.rar"
                    download(file_id, dest)
                    extract(dest, raw / name, expected)
                merge_archives(raw, merged)
                write_marker(merged)
                if cache:
                    maybe_write_tar(cache, merged)
            # free disk: archives and per-scene trees are no longer needed
            shutil.rmtree(raw, ignore_errors=True)

    train_txt, val_txt = build_txt(merged, repo / "dataset", here, f"DATA2021_{args.preset}")
    if max_images:
        train_txt = subsample(train_txt, max_images, train_txt.with_name(train_txt.stem + "_sub.txt"))
        val_txt = subsample(val_txt, max(20, max_images // 5), val_txt.with_name(val_txt.stem + "_sub.txt"))

    resume = ""
    if resume_arg == "auto":
        cand = out / "checkpoint_last.pth"
        resume = str(cand) if cand.exists() else ""
    elif resume_arg != "none":
        resume = resume_arg
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
        "--run-tag", run_tag,
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
