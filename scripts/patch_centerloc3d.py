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
    if "from torchsummary import summary" in text:
        text = text.replace(
            "from torchsummary import summary",
            "try:\n    from torchsummary import summary\nexcept ImportError:\n    summary = None",
        )
    if "from torchstat import stat" in text:
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
    text = text.replace(
        "bbox = np.array([pred_vertex_new[b,y,x,14], pred_vertex_new[b,y,x,15], pred_vertex_new[b,y,x,2], pred_vertex_new[b,y,x,3]], dtype=np.float32)",
        "bbox = np.array([pred_vertex_np[b,y,x,14], pred_vertex_np[b,y,x,15], pred_vertex_np[b,y,x,2], pred_vertex_np[b,y,x,3]], dtype=np.float32)",
    )
    text = text.replace(
        "bbox = np.array([pred_vertex_new[b,y,x,2], pred_vertex_new[b,y,x,3], pred_vertex_new[b,y,x,14], pred_vertex_new[b,y,x,15]], dtype=np.float32)",
        "bbox = np.array([pred_vertex_np[b,y,x,2], pred_vertex_np[b,y,x,3], pred_vertex_np[b,y,x,14], pred_vertex_np[b,y,x,15]], dtype=np.float32)",
    )
    loss.write_text(text, encoding="utf-8")
    print("  patched utils/loss.py (device + detach)")
    print("done")


if __name__ == "__main__":
    main()
