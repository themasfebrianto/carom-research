#!/usr/bin/env python
"""Generate the Colab notebook for CenterLoc3D training on SVLD-3D.

  python scripts/make_colab_notebook.py

Writes notebooks/train_centerloc3d_colab.ipynb.  The notebook only needs the
public repo: it clones carom-research, then calls
scripts/colab_train_centerloc3d.py with a preset.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks" / "train_centerloc3d_colab.ipynb"

REPO_URL = "https://github.com/themasfebrianto/carom-research.git"
CLONE = "/content/carom"


def md(*lines: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [ln + "\n" for ln in lines[:-1]] + [lines[-1]],
    }


def code(*lines: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [ln + "\n" for ln in lines[:-1]] + [lines[-1]],
    }


CELLS = [
    md(
        "# CenterLoc3D on SVLD-3D — Colab training",
        "",
        "Runtime yang dipakai: **L4 GPU** (T4 juga bisa, lebih lambat).",
        "Cek dulu: *Runtime > Change runtime type > L4*.",
        "",
        "Urutan: sel **Setup** → sel **Smoke** (~15 menit) → kalau lolos, sel **Full**.",
        "",
        "Semua hasil (checkpoint, log) masuk ke `/content/drive/MyDrive/centerloc3d`",
        "kalau Drive di-mount. Kalau sesi putus, jalankan ulang sel **Full** —",
        "otomatis resume dari `checkpoint_last.pth`.",
    ),
    md("## 1. Setup (mount Drive, cek GPU, ambil skrip)"),
    code(
        "# Opsional tapi disarankan: checkpoint selamat kalau sesi putus.",
        "from google.colab import drive",
        "drive.mount('/content/drive')",
    ),
    code(
        "!nvidia-smi --query-gpu=name,memory.total --format=csv,noheader",
        "!rm -rf " + CLONE,
        "!git clone -q --depth 1 " + REPO_URL + " " + CLONE,
        "!python -c \"import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())\"",
    ),
    md(
        "## 2. Smoke test (~15 menit)",
        "",
        "Data A-C (3,4 GB) + 200 gambar + 2 epoch. Tujuannya memastikan",
        "unduh, ekstrak, txt, model, loss, dan checkpoint jalan — bukan hasil.",
    ),
    code(
        "!cd " + CLONE + " && python scripts/colab_train_centerloc3d.py --preset smoke",
    ),
    md(
        "## 3. Full training",
        "",
        "Semua arsip (13,5 GB, 14.592 gambar), 50 epoch, batch 8.",
        "",
        "- Perkiraan di L4: ~5-9 jam untuk 50 epoch (diukur dari smoke).",
        "- Kalau sesi putus: jalankan ulang sel ini, resume otomatis.",
        "- Biar sesi berikutnya tidak mengunduh ulang, tambahkan",
        "  `--cache-tar /content/drive/MyDrive/centerloc3d/svld_data.tar`.",
    ),
    code(
        "!cd " + CLONE + " && python scripts/colab_train_centerloc3d.py --preset full",
    ),
    md(
        "## 4. Cek progres",
        "",
        "Log ada di `train_log.csv` dan `checkpoint_last.pth` di folder output.",
    ),
    code(
        "import pandas as pd",
        "from pathlib import Path",
        "",
        "out = Path('/content/drive/MyDrive/centerloc3d')",
        "if not out.exists():",
        "    out = Path('/content/out')",
        "print(sorted(p.name for p in out.glob('*')))",
        "csv = out / 'train_log.csv'",
        "if csv.exists():",
        "    df = pd.read_csv(csv)",
        "    display(df.tail(10))",
        "    display(df[['train_loss', 'val_loss']].plot())",
    ),
]


def main() -> None:
    nb = {
        "cells": CELLS,
        "metadata": {
            "accelerator": "GPU",
            "colab": {"provenance": [], "gpuType": "L4"},
            "kernelspec": {"display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 0,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT} ({len(CELLS)} cells)")


if __name__ == "__main__":
    main()
