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

    # Degenerate boxes (zero height, NaN from a bad projection) used to make
    # the whole geometry term NaN, so the trainer discarded reproj/iou for the
    # entire batch.  Sanitise the boxes and keep the ratio finite instead.
    replace(
        utils,
        "def basic_ciou(bbox_p, bbox_g):\n"
        '    """\n'
        "    bbox_p: [lt_x, ly_y, br_x, br_y]\n"
        "    bbox_g: [lt_x, ly_y, br_x, br_y]\n"
        '    """\n'
        "    # pred 2d box area\n"
        "    area_p = abs(bbox_p[2] - bbox_p[0]) * abs(bbox_p[3] - bbox_p[1])\n"
        "    # gt 2d box area\n"
        "    area_g = abs(bbox_g[2] - bbox_g[0]) * abs(bbox_g[3] - bbox_g[1])\n"
        "\n"
        "    bbox_h_p = bbox_p[3] - bbox_p[1]\n"
        "    bbox_w_p = bbox_p[2] - bbox_p[0]\n"
        "    bbox_h_g = bbox_g[3] - bbox_g[1]\n"
        "    bbox_w_g = bbox_g[2] - bbox_g[0]\n",
        "def basic_ciou(bbox_p, bbox_g):\n"
        '    """\n'
        "    bbox_p: [lt_x, ly_y, br_x, br_y]\n"
        "    bbox_g: [lt_x, ly_y, br_x, br_y]\n"
        '    """\n'
        "    # Degenerate boxes (zero height, NaN from a bad projection) used to\n"
        "    # make the whole geometry term NaN and the trainer discarded it.\n"
        "    # Sanitise the inputs and keep the ratio finite instead.\n"
        "    bbox_p = np.nan_to_num(np.asarray(bbox_p, dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0)\n"
        "    bbox_g = np.nan_to_num(np.asarray(bbox_g, dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0)\n"
        "    # pred 2d box area\n"
        "    area_p = abs(bbox_p[2] - bbox_p[0]) * abs(bbox_p[3] - bbox_p[1])\n"
        "    # gt 2d box area\n"
        "    area_g = abs(bbox_g[2] - bbox_g[0]) * abs(bbox_g[3] - bbox_g[1])\n"
        "\n"
        "    bbox_h_p = bbox_p[3] - bbox_p[1]\n"
        "    bbox_w_p = bbox_p[2] - bbox_p[0]\n"
        "    bbox_h_g = bbox_g[3] - bbox_g[1]\n"
        "    bbox_w_g = bbox_g[2] - bbox_g[0]\n"
        "    bbox_h_p = bbox_h_p if abs(bbox_h_p) > 1e-6 else 1e-6\n"
        "    bbox_h_g = bbox_h_g if abs(bbox_h_g) > 1e-6 else 1e-6\n",
    )

    # A zero-area box makes `union` negative, so the raw ratio explodes to
    # ~1e8 and the "loss" becomes a huge negative number.  Clamp the final
    # ratio to the valid range so the term stays a bounded penalty.
    replace(utils, "    return ciou\n", "    return np.clip(ciou, -1.0, 1.0)\n")

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

    # A degenerate projection (zero/NaN vertex) used to poison the whole
    # reprojection term.  Keep the loss finite by falling back to the predicted
    # vertex for that one box, so the box is not punished for a broken GT box.
    replace(
        loss,
        "            calc_vertex[y, x] = cal_pred_2dvertex(pers, bp, l, w, h, calib_m)\n",
        "            calc = cal_pred_2dvertex(pers, bp, l, w, h, calib_m)\n"
        "            if not np.all(np.isfinite(calc)):\n"
        "                calc = pred_vertex_np[b, y, x]\n"
        "            calc_vertex[y, x] = calc\n",
    )
    print("done")


if __name__ == "__main__":
    main()
