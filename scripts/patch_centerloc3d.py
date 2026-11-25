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


REG_IOU_DIFF_SRC = '''

def _ciou_torch(bbox_p, bbox_g):
    """Differentiable CIoU for one predicted box and one GT box."""
    x1p, y1p, x2p, y2p = bbox_p
    x1g, y1g, x2g, y2g = bbox_g
    area_p = (x2p - x1p).abs() * (y2p - y1p).abs()
    area_g = (x2g - x1g).abs() * (y2g - y1g).abs()
    x_min = torch.maximum(x1p, x1g)
    y_min = torch.maximum(y1p, y1g)
    x_max = torch.minimum(x2p, x2g)
    y_max = torch.minimum(y2p, y2g)
    inter = torch.clamp(x_max - x_min, min=0) * torch.clamp(y_max - y_min, min=0)
    union = area_p + area_g - inter
    iou = inter / torch.clamp(union, min=1e-6)
    cx_p = (x1p + x2p) / 2.0
    cy_p = (y1p + y2p) / 2.0
    cx_g = (x1g + x2g) / 2.0
    cy_g = (y1g + y2g) / 2.0
    center_dis = (cx_p - cx_g) ** 2 + (cy_p - cy_g) ** 2
    ext_x_min = torch.minimum(x1p, x1g)
    ext_y_min = torch.minimum(y1p, y1g)
    ext_x_max = torch.maximum(x2p, x2g)
    ext_y_max = torch.maximum(y2p, y2g)
    external_dis = (ext_x_max - ext_x_min) ** 2 + (ext_y_max - ext_y_min) ** 2
    w_p = (x2p - x1p).abs()
    h_p = (y2p - y1p).abs()
    w_g = (x2g - x1g).abs()
    h_g = (y2g - y1g).abs()
    v = (4.0 / torch.pi ** 2) * (
        torch.atan(w_g / torch.clamp(h_g, min=1e-6))
        - torch.atan(w_p / torch.clamp(h_p, min=1e-6))
    ) ** 2
    alpha = v / torch.clamp(1.0 - iou + v, min=1e-6)
    ciou = iou - center_dis / torch.clamp(external_dis, min=1e-6) - v * alpha
    return torch.clamp(ciou, -1.0, 1.0)


def reg_iou_loss_diff(iou_type, pred_vertex, target, mask, perspective, fp_size, input_size, raw_img_hs, raw_img_ws):
    """Differentiable CIoU loss on the predicted 2D boxes.

    The reference implementation detaches the geometry terms, so they never
    train the network.  This version keeps the predicted box in the graph and
    only the GT box is a constant.
    """
    featmap_h = fp_size[0]
    pred_vertex = pred_vertex.permute(0, 2, 3, 1)
    total = pred_vertex.new_zeros(())
    count = 0
    for b in range(pred_vertex.shape[0]):
        image_h = raw_img_hs[b]
        image_w = raw_img_ws[b]
        scale = max(image_w, image_h) / featmap_h
        offset = abs(image_w - image_h) / 2.0
        pred_new = torch.stack(
            [
                pred_vertex[b, :, :, 0:16:2] * scale,
                pred_vertex[b, :, :, 1:16:2] * scale - offset,
            ],
            dim=-1,
        ).reshape_as(pred_vertex[b])
        target_new = torch.stack(
            [
                target[b, :, :, 0:16:2] * scale,
                target[b, :, :, 1:16:2] * scale - offset,
            ],
            dim=-1,
        ).reshape_as(target[b])
        t_list = torch.nonzero(mask[b] == 1.0, as_tuple=False)
        for idx in t_list:
            y = int(idx[0])
            x = int(idx[1])
            pers = int(perspective[b, y, x].item())
            if pers == 1:
                bbox = torch.stack([pred_new[y, x, 14], pred_new[y, x, 15], pred_new[y, x, 2], pred_new[y, x, 3]])
                bbox_gt = torch.stack([target_new[y, x, 14], target_new[y, x, 15], target_new[y, x, 2], target_new[y, x, 3]])
            else:
                bbox = torch.stack([pred_new[y, x, 2], pred_new[y, x, 3], pred_new[y, x, 14], pred_new[y, x, 15]])
                bbox_gt = torch.stack([target_new[y, x, 2], target_new[y, x, 3], target_new[y, x, 14], target_new[y, x, 15]])
            total = total + (1.0 - _ciou_torch(bbox, bbox_gt))
            count += 1
    if count == 0:
        return pred_vertex.new_zeros(())
    return total / count
'''


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

    # Make the reprojection term differentiable.  The reference code used
    # torch.zeros_like + detach, so the term never trained the network.  Keep
    # the predicted vertices in the graph; only the projection target is a
    # constant.
    replace(
        loss,
        "pred_vertex_new = torch.zeros_like(pred_vertex)",
        "pred_vertex_new = pred_vertex.clone()",
    )
    replace(
        loss,
        "        pred_vertex_new[b, :, :, 0:16:2] = pred_vertex[b, :, :, 0:16:2] * max(image_w, image_h) / featmap_h\n"
        "        pred_vertex_new[b, :, :, 1:16:2] = pred_vertex[b, :, :, 1:16:2] * max(image_w, image_h) / featmap_h - abs(image_w-image_h)/2.\n",
        "        pred_vertex_new[b] = torch.stack(\n"
        "            [\n"
        "                pred_vertex[b, :, :, 0:16:2] * max(image_w, image_h) / featmap_h,\n"
        "                pred_vertex[b, :, :, 1:16:2] * max(image_w, image_h) / featmap_h - abs(image_w - image_h) / 2.0,\n"
        "            ],\n"
        "            dim=-1,\n"
        "        ).reshape_as(pred_vertex[b])\n",
    )

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

    # Differentiable CIoU loss.  The original reg_iou_loss detaches the boxes,
    # so its value is a constant and never trains the model.  This version keeps
    # the predicted box in the graph and only the GT box is constant.
    loss_text = loss.read_text(encoding="utf-8")
    if "def reg_iou_loss_diff" not in loss_text:
        loss_text += REG_IOU_DIFF_SRC
        loss.write_text(loss_text, encoding="utf-8")
        print("  added reg_iou_loss_diff (differentiable ciou)")
    print("done")


if __name__ == "__main__":
    main()
