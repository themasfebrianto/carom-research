# Dataset Kalibrasi untuk Uji GeoCalib / AnyCalib / VP

**Tanggal:** 19 November 2026  
**Tujuan:** catatan pemilihan dataset yang punya parameter kamera diketahui, untuk menguji GeoCalib, AnyCalib, VP, dan anchor.

---

## 1. Ringkasan pilihan

| Dataset | Parameter yang tersedia | Roll? | Distorsi? | Ukuran/akses | Cocok untuk |
|---|---|---|---|---|---|
| **SVLD-3D** | `f`, `h`, pitch, yaw | **tidak** | tidak | Google Drive; 2.237 gambar test | uji cepat `f/pitch/yaw/h` |
| **I24-3D** | `P`, `H`, `H_inv`, `vps`, `corr_pts`, `space_pts`, `curve`; `f/h/yaw/pitch/roll` turunan | **ya, turunan** | tidak | ZIP 49,8 GB; tidak bisa partial | uji lengkap pose + box 3D |
| **I24V** | `H`/`P` static/dynamic per kamera; `f/h/yaw/pitch/roll` turunan | ya, turunan | tidak | 234 kamera, 234 jam; jauh lebih besar | tracking, bukan kalibrasi utama |
| **CUTC** | checkerboard/ChArUco: `K`, pose, tinggi, marker jalan | ya | kemungkinan | cek halaman proyek | GT paling bersih |
| **RoScenes** | intrinsik + ekstrinsik per kamera | ya, turunan | tidak | ModelScope; non-komersial | multi-kamera roadside |
| **BrnoCompSpeed** | `vp1`, `vp2`, `pp`, `scale` | tidak langsung | tidak | minta akses; ~200 GB | video, bukan parameter eksplisit |

**Kesimpulan:** tidak ada dataset publik yang sekaligus memberi `f`, `h`, yaw, pitch, roll, principal point, dan distorsi secara eksplisit. Yang paling lengkap untuk pose pinhole adalah **I24-3D**; yang paling cepat adalah **SVLD-3D**.

---

## 2. SVLD-3D

**Repo:** https://github.com/stjuliet/SVLD-3D-DATASET  
**Test set:** https://drive.google.com/file/d/10zspX_-gWoQOwzN5Ba-MDQVsV6Omh80A/view?usp=sharing

### Isi

- 5 scene, 14.592 train/val + 2.237 test images.
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

### Keterbatasan

- Tidak bisa memvalidasi roll atau `k1` AnyCalib.
- Kalibrasi VWL dari marka jalan, bukan checkerboard.
- Test set hanya 1 truck; jangan klaim validasi truk dari SVLD.

### Rekomendasi

- Unduh **test set** saja.
- Ambil 5 scene × 10 gambar.
- Bandingkan `f`, pitch, yaw, `h`; roll/distorsi tulis sebagai batasan.

---

## 3. I24-3D (BMVC 2023)

**Repo:** https://github.com/I24-MOTION/I24-3D-dataset  
**Data:** https://i24motion.org/ → bagian **I24-3D dataset (BMVC 2023)**  
**Ukuran:** satu ZIP **49,8 GB**; tidak ada download per scene/kamera.

### Isi

- 3 scene, 16–17 kamera 4K, 30 fps.
- 877.000 box 3D, 720 kendaraan unik.
- `data/hg/sceneX_hg.json` per kamera:

```text
corr_pts  - titik korespondensi di citra
space_pts - titik korespondensi di bidang jalan (z=0)
P         - [4,3] space -> image
H         - [3,3] image -> ground
H_inv     - [3,3] ground -> image
curve     - 3 parameter kurva jalan
vps       - 3 pasang VP: longitudinal, lateral, vertical
```

- `data/obj/sceneX_annotations.csv`: `frame,camera,id,x,y,l,w,h,direction,class,gen`; satuan **kaki**.
- `data/spl_obj`, `data/track`, `data/ts`, `video/sceneX/pXcX.mp4`.

### Cara memperoleh parameter

```text
P = K [R | t]
K, R = RQ(P[:, :3])
C = -Rᵀ t
h = C_z (kaki -> meter)
yaw/pitch/roll = dari R
```

- `P` ditulis `[4,3]`; transpose ke 3×4.
- `P` dibangun dari `H_inv` + VP vertikal; `scale_Z` menyetel kolom-Z dengan box known.
- **Bukan checkerboard GT**; sebut **reference calibration**.
- Tidak ada distorsi; principal point hanya dari dekomposisi.
- Round-trip `P` → `corr_pts` wajib; target <1 px.

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
