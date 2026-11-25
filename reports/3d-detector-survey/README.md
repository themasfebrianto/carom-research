# Survey 3D Detector untuk SVLD / CCTV

**Tanggal:** 20 November 2026  
**Tujuan:** mencari 3D detector yang sudah ada (paper/repo/weights) untuk menghasilkan box 3D kendaraan yang cukup akurat bagi kalibrasi f/pose.

---

## 0. Ringkasan

1. **CenterLoc3D adalah model yang paling tepat domainnya**: dibuat khusus untuk SVLD-3D (roadside surveillance), kode MIT, output 8 vertex 2D + dimensi + tipe. **Tetapi tidak ada pretrained weight** di repo; issue #1 meminta weight dan tidak dijawab.
2. **CenterLoc3D juga yang paling cocok untuk kalibrasi**: jaringan hanya melihat gambar (512x512) dan memprediksi vertex/dimensi di image space. Prediksi ini **tidak bergantung pada K**, sehingga bisa dipakai dengan PnP untuk mencari f. Model lain (BEVHeight, CoBEV) memakai K di projection, jadi output 3D-nya bergantung pada kalibrasi yang diberikan.
3. **BEVHeight++ punya pretrained weight** untuk ROPE3D/DAIR-V2X (roadside), MIT, tetapi butuh GPU dan custom CUDA voxel pooling. Ini kandidat terbaik kalau ada GPU dan ingin zero-shot/adaptasi.
4. **CoBEV** juga punya pretrained weight roadside (DAIR-V2X), tetapi berat dan GPU-only.
5. **Pro3D (WACV 2026)** adalah SOTA roadside terbaru, tetapi code/checkpoints belum dirilis (per 20 Nov 2026).
6. **RoadVision3D** adalah library training (MonoLSS/GUPNet/SMOKE) untuk DAIR-V2X/ROPE3D/KITTI; tidak ada model zoo/weights.
7. **MonoDGP / MonoDETR / MonoDINO-DETR** punya weight KITTI dan SOTA onboard, tetapi domainnya dashcam; kemungkinan besar gagal di CCTV high-angle. Butuh custom CUDA ops.
8. **3D-MOOD (ICCV 2025)** punya weight open-set dan bisa CPU via LibreYOLO, tetapi bukan model roadside; belum tentu akurat di SVLD.

**Rekomendasi:** kalau ada GPU, **train CenterLoc3D di SVLD trainval** (kode + dataset sudah ada), lalu pakai 8 vertex + dimensi ke **multi-box PnP** untuk f/pose. Kalau hanya ingin pretrained zero-shot, **BEVHeight++** adalah pilihan roadside yang paling siap, tetapi output-nya bergantung pada K.

---

## 1. Tabel kandidat

| Metode | Domain | Kode | Pretrained | Output | Butuh K? | Catatan |
|---|---|---|---|---|---|---|
| **CenterLoc3D** | roadside / SVLD-3D | MIT | **tidak** | tipe, centroid, 8 vertex 2D, dimensi | tidak (network); K dipakai setelahnya | Paling tepat domain; weight tidak dirilis |
| **BEVHeight++** | roadside ROPE3D/DAIR-V2X | MIT | **ya** (Tsinghua cloud) | BEV 3D box | ya | GPU + CUDA voxel pooling |
| **BEVHeight** | roadside ROPE3D/DAIR-V2X | MIT | ya | BEV 3D box | ya | GPU |
| **CoBEV** | roadside DAIR-V2X | MIT | ya (Baidu/Google Drive) | BEV 3D box | ya | GPU, berat |
| **Pro3D** | roadside DAIR-V2X/ROPE3D | belum | belum | BEV 3D box | ya | WACV 2026, code/ckpt belum |
| **RoadVision3D** | roadside DAIR-V2X/ROPE3D/KITTI | Apache 2.0 | tidak | 3D box (MonoLSS/GUPNet/SMOKE) | ya | Library training, bukan model zoo |
| **MonoDGP** | KITTI onboard | MIT | ya | 3D box | ya | SOTA KITTI; CUDA ops; domain beda |
| **MonoDETR** | KITTI onboard | MIT | ya | 3D box | ya | ICCV 2023; CUDA ops |
| **MonoDINO-DETR** | KITTI onboard | belum jelas | sebagian | 3D box | ya | DINOv2 + Depth Anything V2 |
| **3D-MOOD** | open-set Omni3D | Apache 2.0 | ya (HuggingFace) | 3D box camera coords | ya | Bisa CPU via LibreYOLO; bukan roadside |
| **MonoSOWA** | KITTI-360 auto-label | ya | ya | 3D box | ya | Untuk auto-label, bukan roadside |

---

## 2. CenterLoc3D (paling relevan)

- Paper: *CenterLoc3D: Monocular 3D Vehicle Localization Network for Roadside Surveillance Cameras* (Complex & Intelligent Systems, 2023; arXiv:2203.14550).
- Repo: <https://github.com/stjuliet/CenterLoc3D> (MIT).
- Dataset: <https://github.com/stjuliet/SVLD-3D-DATASET>.
- Arsitektur: ResNet-50 + CenterNet-style multi-task head; input 512x512; output heatmap, 2D offset, 8 vertex 2D, dimensi (L,W,H), tipe kendaraan.
- Hasil paper di SVLD-3D test: **AP3D 51.30% (IoU 0.7)**, **3D localization precision 98%**, **3D dimension precision 85%**, 41 FPS di GTX 1080Ti.
- **Tidak ada pretrained weight** di repo; issue #1 meminta file `../logs/resnet50-Epoch100-...pth` dan belum dijawab. Komentar issue: user lain retrain sendiri, converge cepat, tetapi **overfit ke road scene di training set**.
- Keterbatasan paper: error naik saat pan angle kamera mendekati 0 deg (fitur panjang kendaraan tidak lengkap).
- Implikasi: untuk kamera tetap, fine-tune per scene masih masuk akal; untuk generalisasi lintas lokasi, perlu data beragam/augmentasi.
- **Uji forward pass CPU**: kode berjalan di PyTorch 2.13 setelah `pip install torchsummary torchstat`; 34,95M parameter, ~1,5 s/citra 512x512. Output: heatmap (3,128,128), center offset (2,128,128), vertex (16,128,128), size (3,128,128). Siap dipakai begitu ada weight/hasil training.

### Kenapa penting untuk kalibrasi

Network hanya menerima gambar; 8 vertex dan dimensi adalah prediksi image-space. Kalibrasi K dipakai **setelah** network untuk mengubah centroid/vertex menjadi 3D. Jadi:

1. Jalankan CenterLoc3D pada gambar -> 8 vertex 2D + dimensi.
2. Gunakan `box_pnp_known_dims.py` / solver multi-box untuk mencari f, pitch, yaw, h.
3. Karena satu box lokal ambigu, gabungkan 10-30 kendaraan per scene (kamera sama) dan selesaikan f secara joint.

Ini adalah pipeline yang paling masuk akal: detector khusus domain + PnP kalibrasi.

---

## 3. BEVHeight / BEVHeight++ (pretrained roadside)

- Repo: <https://github.com/ADLab-AutoDrive/BEVHeight> (CVPR 2023, MIT).
- BEVHeight++: <https://github.com/yanglei18/BEVHeight_Plus> (2024/2025, MIT).
- Pretrained weight dirilis 2025/02/03 untuk DAIR-V2X-I dan ROPE3D (Tsinghua cloud), termasuk varian KITTI/KITTI-360/Waymo.
- Metode: height-based BEV, lebih robust terhadap perubahan pitch/roll/focal dibanding BEVDepth.
- **Butuh GPU** dan custom CUDA `voxel_pooling`; tidak ada jalur CPU yang praktis.
- Output 3D box bergantung pada K dan extrinsics yang diberikan. Untuk kalibrasi, ini bukan sumber independen; bisa dipakai kalau K awal sudah dari container/datasheet, lalu di-refine.

**Kapan dipakai:** jika ada GPU dan ingin zero-shot/adaptasi cepat pada citra roadside. Domain ROPE3D/DAIR-V2X lebih dekat ke CCTV daripada KITTI.

---

## 4. CoBEV (pretrained roadside)

- Repo: <https://github.com/MasterHow/CoBEV> (IEEE T-IP 2024, MIT).
- Pretrained model di Baidu Cloud/Google Drive.
- Depth + height complementarity; hasil baik di DAIR-V2X-I, tahan noise focal/roll/pitch.
- Berat, GPU-only, custom ops.

**Kapan dipakai:** alternatif BEVHeight++ kalau weight/arsitektur lebih cocok; tetap butuh GPU dan K awal.

---

## 5. Pro3D (WACV 2026, SOTA roadside)

- Repo: <https://github.com/cc50121/Pro3D>.
- Paper: *Roadside Monocular 3D Detection Prompted by 2D Detection* (arXiv:2404.01064).
- Menggunakan 2D detector sebagai prompt + scene prior (background image) + BEV; SOTA di DAIR-V2X-I.
- **Checklist repo: training code, checkpoints, inference code belum dirilis** (hanya notebook demo + initialization).
- Belum bisa dipakai sampai code/weight keluar.

---

## 6. RoadVision3D (library training)

- Repo: <https://github.com/jborau/RoadVision3D> (Apache 2.0).
- Implementasi MonoLSS, GUPNet, SMOKE; dataset DAIR-V2X, ROPE3D, KITTI.
- Instalasi CPU didukung, tetapi tidak ada model zoo/weight; harus training sendiri.
- Cocok kalau ingin membandingkan beberapa model roadside dalam satu framework, tetapi bukan solusi siap pakai.

---

## 7. Model KITTI (MonoDGP, MonoDETR, MonoDINO-DETR)

- MonoDGP: <https://github.com/PuFanqi23/MonoDGP> (CVPR 2025, MIT), weight tersedia.
- MonoDETR: <https://github.com/ZrrSkywalker/MonoDETR> (ICCV 2023, MIT), weight tersedia.
- MonoDINO-DETR: <https://github.com/JihyeokKim/MonoDINO-DETR> (IV 2025), DINOv2 + Depth Anything V2.
- Semua memakai deformable attention / custom CUDA ops dan dilatih pada KITTI onboard.
- Untuk CCTV high-angle, domain gap besar: KITTI camera rendah, FOV sedang, kendaraan besar di gambar. Zero-shot kemungkinan buruk.
- Tetap bisa menjadi **pretrained initialization** untuk fine-tune di SVLD, tetapi CenterLoc3D lebih tepat karena sudah dilatih pada SVLD.

---

## 8. 3D-MOOD (open-set, bisa CPU)

- Repo: <https://github.com/cvg/3D-MOOD> (ICCV 2025, Apache 2.0).
- Weight di HuggingFace; demo CPU via LibreYOLO (`Libre3DMOOD(device="cpu")`).
- Output 3D box di camera coordinates (center, dimensions, quaternion) + confidence; butuh intrinsics.
- Dilatih pada Omni3D (KITTI, nuScenes, Argoverse, dll), bukan roadside khusus.
- Bisa dicoba zero-shot pada 1-2 citra SVLD untuk melihat apakah box-nya masuk akal; jangan berharap akurasi kalibrasi.

---

## 9. Implikasi untuk kalibrasi

1. **Detector yang butuh K tidak bisa menjadi sumber f independen.** BEVHeight/CoBEV/Pro3D memproyeksikan fitur dengan K; kalau K salah, box 3D salah. Mereka bisa memverifikasi/refine K awal, bukan menggantikannya.
2. **CenterLoc3D adalah pengecualian**: output 8 vertex/dimensi adalah image-space, jadi bisa dipakai untuk PnP. Ini alasan utama CenterLoc3D lebih menarik daripada model yang lebih baru.
3. **Satu box lokal ambigu** (lihat `reports/svld-vehicle-vp/README.md` 3.5). Gunakan 10-30 box per scene dan joint solve f/pose; atau berikan constraint ground plane/yaw.
4. **Akurasi dimensi 85%** dari paper berarti error ~15%; f error dari satu box bisa ~5-6%. Dengan banyak box dan robust median, target 2-3% mungkin; belum cukup untuk metrologi +/-1%, tetapi lebih baik dari model f generik.
5. **Container 20 ft** tetap anchor f paling akurat (0,2%) jika tersedia. Detector 3D adalah untuk lokasi tanpa container.

---

## 10. Rekomendasi langkah

1. **Jika ada GPU:** train CenterLoc3D di SVLD trainval (14.592 gambar, 3 kelas) mengikuti paper (ResNet-50, 512x512, 100 epoch, GTX 1080Ti). Notebook Colab siap: `notebooks/train_centerloc3d_colab.ipynb`. Notebook sudah menangani patch NumPy 2/PyTorch 2, generate txt, AMP, checkpoint ke Drive, dan resume. Setelah itu:
   - jalankan di SVLD test -> 8 vertex + dimensi;
   - multi-box PnP -> f/pitch/yaw/h;
   - bandingkan dengan GT XML.
2. **Jika hanya ingin pretrained zero-shot dan ada GPU:** coba BEVHeight++ (ROPE3D/DAIR-V2X) pada 20 citra SVLD, dengan K GT; ukur dimensi/posisi/yaw. Kemungkinan perlu fine-tune.
3. **Jika CPU-only:** coba 3D-MOOD via LibreYOLO pada 1-2 citra; ekspektasi rendah. Jangan jadikan jalur utama.
4. **Tanpa GPU dan tanpa training:** tetap pakai container/datasheet/manual 8-corner; detector 3D belum siap.

---

## 11. Link

- CenterLoc3D: <https://github.com/stjuliet/CenterLoc3D>
- SVLD-3D: <https://github.com/stjuliet/SVLD-3D-DATASET>
- BEVHeight: <https://github.com/ADLab-AutoDrive/BEVHeight>
- BEVHeight++: <https://github.com/yanglei18/BEVHeight_Plus>
- CoBEV: <https://github.com/MasterHow/CoBEV>
- Pro3D: <https://github.com/cc50121/Pro3D>
- RoadVision3D: <https://github.com/jborau/RoadVision3D>
- MonoDGP: <https://github.com/PuFanqi23/MonoDGP>
- MonoDETR: <https://github.com/ZrrSkywalker/MonoDETR>
- 3D-MOOD: <https://github.com/cvg/3D-MOOD>
- MonoSOWA: <https://github.com/jskvrna/MonoSOWA>

---

## 12. Colab training

Notebook: `notebooks/train_centerloc3d_colab.ipynb`

Isi notebook:

1. cek GPU T4;
2. mount Google Drive;
3. clone CenterLoc3D + install `torchsummary`, `torchstat`, `gdown`;
4. patch NumPy 2/PyTorch 2 (`np.float`, scalar assignment, `.cuda()` di loss);
5. download Scene A-C atau pakai folder di Drive;
6. generate `DATA2021_scene_train.txt` / `_val.txt` (hanya gambar yang ada);
7. train `session0_center` 20 epoch, batch 8, AMP, checkpoint ke Drive;
8. cell resume setelah disconnect.

Perkiraan: `session0_center` 2.851 train + 313 val, ~2-3 menit/epoch di T4 dengan AMP; 20 epoch ~45-60 menit. Full 5 scene ~9 menit/epoch; 20 epoch ~3 jam (perlu checkpoint/resume).

Script pendukung:

- `scripts/train_centerloc3d_colab.py` - training loop + AMP + checkpoint/resume.
- `scripts/make_centerloc3d_txt.py` - generate annotation lines, skip gambar yang tidak ada.
- `scripts/patch_centerloc3d.py` - patch kompatibilitas NumPy 2/PyTorch 2.
- `scripts/make_colab_notebook.py` - generator notebook.

Catatan: notebook memakai `session0_center` (Scene A-C) dulu. Untuk `0cam`/`1cam`/`session6_right`, download Scene D/E dan merge `DATA2021` (cell terakhir di notebook).
