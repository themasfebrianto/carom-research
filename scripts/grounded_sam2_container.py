#!/usr/bin/env python
"""Grounding DINO + SAM 2: segment a shipping container from text.

Run with the grounded-sam2 environment:
  & "...\grounded-sam2\Scripts\python.exe" scripts\grounded_sam2_container.py ^
    --image out\timepass\truck86.jpg --prompt "shipping container."
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import (
    AutoModelForZeroShotObjectDetection,
    AutoProcessor,
    Sam2Model,
    Sam2Processor,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--prompt", default="shipping container.")
    ap.add_argument("--box", default="", help="manual container box x1,y1,x2,y2; skips Grounding DINO")
    ap.add_argument("--out", default=r"out\timepass")
    ap.add_argument("--box-threshold", type=float, default=0.2)
    ap.add_argument("--text-threshold", type=float, default=0.2)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    image_pil = Image.open(args.image).convert("RGB")
    image_bgr = cv2.imread(args.image)

    print("using manual container box" if args.box else "loading Grounding DINO...", flush=True)
    if args.box:
        boxes = torch.tensor([[float(x) for x in args.box.split(",")]])
        scores = torch.tensor([1.0])
        labels = ["manual box"]
    else:
        gd_processor = AutoProcessor.from_pretrained("IDEA-Research/grounding-dino-tiny")
        gd_model = AutoModelForZeroShotObjectDetection.from_pretrained(
            "IDEA-Research/grounding-dino-tiny"
        ).to(args.device)
        inputs = gd_processor(images=image_pil, text=args.prompt, return_tensors="pt").to(args.device)
        with torch.no_grad():
            outputs = gd_model(**inputs)
        results = gd_processor.post_process_grounded_object_detection(
            outputs,
            inputs.input_ids,
            threshold=args.box_threshold,
            text_threshold=args.text_threshold,
            target_sizes=[image_pil.size[::-1]],
        )[0]
        boxes = results["boxes"].cpu()
        scores = results["scores"].cpu()
        labels = results.get("labels", results.get("text_labels", []))
    print(f"detections: {len(boxes)}")
    for b, s, l in zip(boxes, scores, labels):
        print(f"  {l}  score={float(s):.3f}  box={[round(float(v),1) for v in b]}")

    if len(boxes) == 0:
        return

    print("loading SAM 2...", flush=True)
    sam_processor = Sam2Processor.from_pretrained("facebook/sam2.1-hiera-tiny")
    sam_model = Sam2Model.from_pretrained("facebook/sam2.1-hiera-tiny").to(args.device)

    # SAM 2 expects a list of boxes per image.
    sam_inputs = sam_processor(
        images=image_pil,
        input_boxes=[boxes.tolist()],
        return_tensors="pt",
    ).to(args.device)
    with torch.no_grad():
        sam_outputs = sam_model(**sam_inputs, multimask_output=False)
    masks = sam_processor.post_process_masks(
        sam_outputs.pred_masks.cpu(),
        sam_inputs["original_sizes"].cpu(),
    )[0]
    masks = masks.numpy()
    if masks.ndim == 4:
        masks = masks[:, 0]
    print("masks:", masks.shape)

    vis = image_bgr.copy()
    for i, (mask, box, score) in enumerate(zip(masks, boxes, scores)):
        m = mask > 0.5
        color = np.array([0, 0, 255], dtype=np.uint8)
        vis[m] = (0.6 * vis[m] + 0.4 * color).astype(np.uint8)
        x1, y1, x2, y2 = [int(v) for v in box]
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(vis, f"{float(score):.2f}", (x1, max(15, y1 - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        np.save(out_dir / f"container_mask_{i}.npy", m)
        cv2.imwrite(out_dir / f"container_mask_{i}.png", (m * 255).astype(np.uint8))

    out_path = out_dir / "grounded_sam2_container.jpg"
    cv2.imwrite(str(out_path), vis)
    print("saved", out_path)


if __name__ == "__main__":
    main()
