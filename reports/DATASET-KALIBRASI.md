# Dataset Kalibrasi untuk Uji GeoCalib / AnyCalib / VP

**Tanggal:** 19 November 2026  
**Tujuan:** catatan pemilihan dataset yang punya parameter kamera diketahui, untuk menguji GeoCalib, AnyCalib, VP, dan anchor.

---

## 1. Ringkasan pilihan

| Dataset | Parameter yang tersedia | Roll? | Distorsi? | Ukuran/akses | Cocok untuk |
|---|---|---|---|---|---|
| **SVLD-3D** | `f`, `h`, pitch, yaw; `veh_size` preset | **tidak** | tidak | Google Drive; test 2.237 + trainval 14.592 gambar | kalibrasi + geometri; **bukan** akurasi dimensi fisik |
| **I24-3D** | `P`, `H`, `H_inv`, `vps`, `corr_pts`, `space_pts`, `curve`; `f/h/yaw/pitch/roll` turunan **tidak konsisten** (lihat §3.1) | **tidak** (RQ tidak sah) | tidak | ZIP 49,8 GB; tidak bisa partial | box 3D & ground-plane, **bukan** f/pose |
| **I24V** | `H`/`P` static/dynamic per kamera; `f/h/yaw/pitch/roll` turunan | ya, turunan | tidak | 234 kamera, 234 jam; jauh lebih besar | tracking, bukan kalibrasi utama |
| **CUTC** | checkerboard/ChArUco: `K`, pose, tinggi, marker jalan | ya | kemungkinan | cek halaman proyek | GT paling bersih |
| **RoScenes** | intrinsik + ekstrinsik per kamera | ya, turunan | tidak | ModelScope; non-komersial | multi-kamera roadside |
| **BrnoCompSpeed** | `vp1`, `vp2`, `pp`, `scale` | tidak langsung | tidak | minta akses; ~200 GB | video, bukan parameter eksplisit |

**Kesimpulan:** tidak ada dataset publik yang sekaligus memberi `f`, `h`, yaw, pitch, roll, principal point, dan distorsi secara eksplisit. Untuk `f`/pitch/yaw/h, **SVLD-3D** paling cepat. **I24-3D tidak memberi f/pose yang konsisten**; `P`-nya adalah model tracking, bukan matriks kamera terkalibrasi (lihat §3.1).

---

## 2. SVLD-3D

**Repo:** https://github.com/stjuliet/SVLD-3D-DATASET  
**Test set:** https://drive.google.com/file/d/10zspX_-gWoQOwzN5Ba-MDQVsV6Omh80A/view?usp=sharing

### Isi

- 5 scene, 14.592 train/val + 2.237 test images. Trainval: 39.477 objek (37.611 Car, 1.166 Bus, **700 Truck**).
- Roadside camera; 8 sudut box 3D + `veh_size`.
- `Calib/{scene_id}.xml`:

```text
f     = focal length (px)
fi    = pitch (rad)
theta = yaw (rad)
h     = camera height (mm)
```

- `cx,cy` = tengah citra (`w/2, h/2`), bukan parameter terpisah.
- **Roll tidak ada.** Paper menyatakan roll hanya rotasi citra dan tidak memengaruhi kalibrasi.
- **Distorsi tidak ada.** Model pinhole.

> **Catatan 19 November 2026 — `veh_size` adalah preset, bukan pengukuran.** Trainval: **1.164/1.166 Bus** `L=12,60 m`; 184 Truck `L=20,00 m`; test: Bus `12,00/9,46 m`. Car juga memakai 116 nilai `L` unik untuk 37.611 objek. Fit 8 sudut karena itu **self-consistency**, bukan akurasi fisik. Kalibrasi tetap sah (trainval 5 scene: median 0,73–0,84 px, 0 objek >2 px). Detail: `svld-trainval/README.md`.

### Keterbatasan

- Tidak bisa memvalidasi roll atau `k1` AnyCalib.
- Kalibrasi VWL dari marka jalan, bukan checkerboard.
- Test set hanya 1 truck; **trainval punya 700 Truck + 1.166 Bus**, tetapi `veh_size` preset — gunakan untuk stress-test, bukan accuracy claim.

### Rekomendasi

- Test set untuk evaluasi; trainval 14.592 gambar untuk stress-test truk/bus.
- Ambil 5 scene × 10 gambar untuk uji cepat.
- Bandingkan `f`, pitch, yaw, `h`; roll/distorsi tulis sebagai batasan.

---

## 3. I24-3D (BMVC 2023)

**Repo:** https://github.com/I24-MOTION/I24-3D-dataset  
**Data:** https://i24motion.org/ → bagian **I24-3D dataset (BMVC 2023)**  
**Ukuran:** satu ZIP **49,8 GB**; tidak ada download per scene/kamera.

### Isi

- 3 scene, 16–18 kamera 4K, 30/60 fps.
- 876.948 box 3D, 720 kendaraan unik.
- `data/hg/sceneX_hg.json` **per arah** (EB/WB), lalu per kamera:

```text
{"EB": {"p1c1": {...}}, "WB": {...}}
corr_pts  - titik korespondensi di citra
space_pts - titik korespondensi di bidang jalan (z=0)
P         - 3x4 space -> image (bukan 4x3; kolom-Z dari VP vertikal)
H         - [3,3] image -> ground
H_inv     - [3,3] ground -> image
curve     - 3 parameter kurva jalan
vps       - 3 VP: longitudinal, lateral, vertical
```

- `data/obj/sceneX_annotations.csv`: `frame,camera,id,x,y,l,w,h,direction,class,gen`; satuan **kaki**.
- `data/spl_obj`, `data/track`, `data/ts`, `video/sceneX/pXcX.mp4`.

### Cara memperoleh parameter

> **Koreksi 19 November 2026:** langkah RQ di bawah **bukan** cara yang sah untuk
> I24-3D. `P[:,2]` adalah kolom VP vertikal dengan skala arbitrer (`* 0.01` di
> `homography.py`) yang kemudian disesuaikan `scale_Z()` memakai tinggi box.
> RQ(`P`) hanya diagnostik dan tidak menghasilkan K pinhole fisik. Lihat §3.1.

```text
P = K [R | t]              # TIDAK berlaku untuk I24-3D
K, R = RQ(P[:, :3])        # hanya diagnostik
C = -Rᵀ t
h = C_z (kaki -> meter)
yaw/pitch/roll = dari R
```

- `P` di file ditulis **3×4** (bukan 4×3 seperti README); parser menerima keduanya.
- `P` dibangun dari `H_inv` + VP vertikal; `scale_Z` menyetel kolom-Z dengan box known.
- **Bukan checkerboard GT**; sebut **reference reconstruction**, bukan calibration.
- Tidak ada distorsi; principal point hanya dari dekomposisi dan sering tidak fisik.
- Round-trip ground-plane (`H_inv` → `corr_pts`) median **3,89 px**, tidak ada yang <1 px.

### 3.1 Temuan 19 November 2026 (data nyata)

Dataset lengkap sudah diperiksa; laporan: `i24-3d-kalibrasi/README.md`.

- **102 kalibrasi** (EB/WB × kamera). `P` 3×4; `H_inv` konsisten dengan `P[:, [0,1,3]]`.
- **EB vs WB untuk kamera yang sama**: `f` berbeda median **7,1%**, p90 **24,6%**, maks **30,6%**. Intrinsik seharusnya identik; ini membuktikan `f` dari `P` bukan GT.
- Hanya **39/102** K yang plausibel (fx≈fy, principal point di 40% tengah); contoh ekstrem `fx=162`, `fy=452`, `cy=7.054`.
- Ground RMS `H_inv(corr_pts)` median **3,89 px**, maks **9,36 px**; 0/102 <1 px.
- `vps` identik untuk semua 102 kalibrasi dan tidak cocok dengan horizon `H`; jangan pakai sebagai GT per kamera.
- Ketinggian kamera median **34 m** (90% di **28–45 m**), menghadap ke bawah **17–75°** (p2c3 hampir nadir). Ini **bukan side-view** dan bukan CCTV 6–12 m.
- GeoCalib pada 3 kamera × 3 scene: `f` meleset **−52% s/d +26%**; pitch meleset **9–65°**. Gerbang Δf/f <5% dan Δpitch <2° tidak dapat dijalankan.
- **Yang tetap sah:** `L/W/H` 3D (876.948 box, 720 objek), ground-plane localization, tracking, prior dimensi semi/truck.

### Keterbatasan

- Satu ZIP 49,8 GB; tidak bisa ambil `scene1_hg.json` saja.
- 4K video; butuh disk/CPU besar.
- `P` bukan pengukuran fisik langsung.
- Domain jalan tol AS.

### Opsi download

1. Download `README_(I24-3D).txt` 3,2 KB dan “I24-3D data usage utilities” dulu.
2. Minta subset ke penulis: `scene1_hg.json` + annotations + satu video.
3. Kalau harus penuh: download manager dengan resume; 49,8 GB.
4. Jangan unduh untuk laporan hari ini.

---

## 4. I24V (WACV 2024) — bukan pengganti I24-3D

- 234 kamera 1080p, 234 jam, 4,2 mil.
- Fokus **tracking**; 270 pass GPS GT; deteksi 159 juta.
- `annotations/hg/static|dynamic|reference`: `H`/`P` per kamera, WB/EB.
- `P` 3×4; `H` 3×3; parameter bisa diturunkan.
- Tidak ada 8 sudut box 3D seperti I24-3D.
- **Lebih besar** dari I24-3D; bukan jalan pintas ukuran.
- Kalau bisa unduh hanya `annotations/hg` + `reference` 1080p, itu kecil; tetapi paket dataset biasanya besar.

---

## 5. Repo I24-3D: fungsinya apa?

Repo `I24-MOTION/I24-3D-dataset` adalah **toolkit**, bukan dataset.

| File | Fungsi |
|---|---|
| `dataset_README.txt` | struktur file + format `P/H/vps` |
| `homography.py` | `H/H_inv/P`, konversi image↔space↔state, `test_transformation`, `scale_Z`, curve |
| `scene.py` | `Scene`: load anotasi/timestamp/homografi, viewer/annotator |
| `datareader.py` | baca video multi-kamera via NVIDIA VPF |
| `export_dataset.py` | cache frame 4K → 1080p (>100 GB) |
| `multitask_dataset.py` | dataset PyTorch, label 8 corners/state |
| `evaluate.py` | clearMOT/HOTA tracking |
| `evaluate_detector_new.py` | evaluasi detektor |
| `train.py`, `load_model.py` | training/load model RetinaNet legacy |
| `single_frame_labeler.py` | anotasi single-frame |
| `lp_redact.py` | redaksi plat |
| `issue_tracker.csv` | error anotasi |

**Yang tidak ada:** video/anotasi/`hg.json`, tabel `f/h/yaw/pitch/roll`, script GeoCalib/AnyCalib.

---

## 6. Rekomendasi untuk laporan

1. **Hari ini:** pakai Cawang + LearnPinhole + SVLD-3D; jangan download I24 49,8 GB.
2. **I24-3D nanti:** mulai dari `README_(I24-3D).txt` + `dataset_README.txt`; minta subset; parse `scene1_hg.json`.
3. **Label GT:** I24 = reference calibration; SVLD = VWL reference; CUTC/checkerboard = lab GT.
4. **Jangan klaim:** distorsi/principal point dari I24; roll dari SVLD.
5. **Untuk roll:** I24-3D/I24V/CUTC; bukan SVLD.
6. **Untuk distorsi:** CUTC/checkerboard; bukan I24/SVLD.

---

## 7. Link

- SVLD repo: https://github.com/stjuliet/SVLD-3D-DATASET
- SVLD test set: https://drive.google.com/file/d/10zspX_-gWoQOwzN5Ba-MDQVsV6Omh80A/view?usp=sharing
- I24-3D repo: https://github.com/I24-MOTION/I24-3D-dataset
- I24-3D data: https://i24motion.org/
- OpenTrafficCam3D/CUTC: https://github.com/kvuong2711/OpenTrafficCam3D
- RoScenes: https://github.com/roscenes/RoScenes
