#!/usr/bin/env python
"""Apply NumPy 2 / PyTorch 2 compatibility patches to CenterLoc3D.

The official repo targets Python 3.6, PyTorch 1.8 and NumPy 1.x.  Colab uses
newer versions.  These replacements are small and keep the original math.

  python patch_centerloc3d.py --repo /content/CenterLoc3D
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def replace(path: Path, old: str, new: str, required: bool = True) -> bool:
    text = path.read_text(encoding="utf-8")
    if new in text:
        print(f"  already patched: {path.name}")
        return True
    if old not in text:
        if required:
            print(f"  NOT FOUND in {path}: {old[:70]!r}")
        return False
    path.write_text(text.replace(old, new), encoding="utf-8")
    print(f"  patched {path.name}")
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    args = ap.parse_args()
    repo = Path(args.repo)

    utils = repo / "utils" / "utils.py"
    text = utils.read_text(encoding="utf-8")
    new = re.sub(r"np\.float\b", "float", text)
    if new != text:
        utils.write_text(new, encoding="utf-8")
        print("  patched utils/utils.py (np.float -> float)")
    else:
        print("  already patched: utils/utils.py")

    dl = repo / "dataset" / "dataloader.py"
    replace(dl, "box_cls_id = int(box_cls[i])", "box_cls_id = int(box_cls[i].item())")
    replace(
        dl,
        "batch_box_perspective[ct_int[1], ct_int[0]] = box_perspective[i]",
        "batch_box_perspective[ct_int[1], ct_int[0]] = box_perspective[i].item()",
    )

    # torchsummary/torchstat are only used for printing model stats, but they are
    # imported at module level and are old enough to be fragile on Colab.
    fpn = repo / "nets" / "fpn.py"
    text = fpn.read_text(encoding="utf-8")
    if "except ImportError" in text:
        print("  already patched: nets/fpn.py")
    else:
        text = text.replace(
            "from torchsummary import summary",
            "try:\n    from torchsummary import summary\nexcept ImportError:\n    summary = None",
        )
        text = text.replace(
            "from torchstat import stat  # calc flops",
            "try:\n    from torchstat import stat  # calc flops\nexcept ImportError:\n    stat = None",
        )
        fpn.write_text(text, encoding="utf-8")
        print("  patched nets/fpn.py (optional stats imports)")

    loss = repo / "utils" / "loss.py"
    text = loss.read_text(encoding="utf-8")
    text = text.replace(
        ".type(torch.FloatTensor).cuda()",
        ".type(torch.FloatTensor).to(pred_vertex.device)",
    )
    if "pred_vertex_np = pred_vertex_new.detach()" not in text:
        text = text.replace(
            "        t_list = np.where(mask[b].cpu() == 1.0)  # all object",
            "        pred_vertex_np = pred_vertex_new.detach().cpu().numpy()\n"
            "        t_list = np.where(mask[b].cpu() == 1.0)  # all object",
        )

    # --- GPU fixes -------------------------------------------------------
    # The original code builds numpy arrays straight from CUDA tensors, which
    # only works when the tensors live on the CPU.  Everything below moves the
    # values to the host first; gradients are unaffected because these terms
    # are detached in the reference implementation too.
    gpu_fixes = [
        (
            "        calib_m = calib_matrix[b]\n",
            "        calib_m = calib_matrix[b].detach().cpu().numpy()\n",
        ),
        (
            "            pers = perspective[b, y, x]\n"
            "            bp = base_point[b, y, x]\n"
            "            l = pred_box_size[b, 0, y, x]\n"
            "            w = pred_box_size[b, 1, y, x]\n"
            "            h = pred_box_size[b, 2, y, x]\n",
            "            pers = int(perspective[b, y, x].item())\n"
            "            bp = base_point[b, y, x].detach().cpu().numpy()\n"
            "            l = float(pred_box_size[b, 0, y, x])\n"
            "            w = float(pred_box_size[b, 1, y, x])\n"
            "            h = float(pred_box_size[b, 2, y, x])\n",
        ),
        (
            "        pred_vertex_np = pred_vertex_new.detach().cpu().numpy()\n"
            "        t_list = np.where(mask[b].cpu() == 1.0)  # all object\n"
            "        for y, x in zip(t_list[0], t_list[1]):\n"
            "            pers = perspective[b, y, x]\n"
            "            if pers == 1:   # right view\n",
            "        pred_vertex_np = pred_vertex_new.detach().cpu().numpy()\n"
            "        target_np = target_new.detach().cpu().numpy()\n"
            "        t_list = np.where(mask[b].cpu() == 1.0)  # all object\n"
            "        for y, x in zip(t_list[0], t_list[1]):\n"
            "            pers = int(perspective[b, y, x].item())\n"
            "            if pers == 1:   # right view\n",
        ),
        (
            "target_new[b,y,x,",
            "target_np[b,y,x,",
        ),
        (
            "pred_vertex_new[b,y,x,",
            "pred_vertex_np[b,y,x,",
        ),
        (
            "l = float(pred_box_size[b, 0, y, x])",
            "l = float(pred_box_size[b, 0, y, x].detach())",
        ),
        (
            "w = float(pred_box_size[b, 1, y, x])",
            "w = float(pred_box_size[b, 1, y, x].detach())",
        ),
        (
            "h = float(pred_box_size[b, 2, y, x])",
            "h = float(pred_box_size[b, 2, y, x].detach())",
        ),
        (
            "cdiou = basic_cdiou(pred_vertex_new[b,y,x], target_new[b,y,x], bbox, bbox_gt)",
            "cdiou = basic_cdiou(pred_vertex_np[b,y,x], target_np[b,y,x], bbox, bbox_gt)",
        ),
    ]
    applied = 0
    for old, new in gpu_fixes:
        if new in text or new == old:
            continue
        if old in text:
            text = text.replace(old, new)
            applied += 1
    loss.write_text(text, encoding="utf-8")
    print(f"  patched utils/loss.py (device + detach + {applied} GPU fixes)")
    print("done")


if __name__ == "__main__":
    main()
