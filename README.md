# Riset CAROM Air → CCTV

Kajian adaptasi metode CAROM Air (drone) untuk pengukuran dimensi kendaraan dari kamera CCTV statis, beserta kalibrasi pada rekaman nyata dan prosedur operasionalnya.

## Dokumen

| Berkas | Isi |
|---|---|
| `RISET-CAROM-Air-untuk-CCTV.md` | Laporan riset utama: formulasi CAROM Air, analisis rezim geometri, derivasi formula pengukuran, anggaran galat, dan penilaian kelayakan |
| `KALIBRASI-CCTV-CAWANG-REV2.md` | Kalibrasi pada rekaman nyata (720p, jalan tol). **Dokumen kalibrasi yang berlaku** |
| `AUDIT-16-15-44.md` | Audit rekaman kedua (480×360 substream) — **tidak layak**, beserta analisis penyebabnya |
| `KALIBRASI-CCTV-CAWANG.md` | Revisi 1 kalibrasi. **Digantikan** — angka $f$, $h$, $w$ di dalamnya tidak sahih |
| `SOP-KALIBRASI-CCTV.md` | Prosedur operasional kalibrasi, berlaku umum untuk CCTV mana pun |
| `SOP-PENGUKURAN-DIMENSI-KENDARAAN.md` | Prosedur operasional pengukuran dimensi kendaraan |

## Temuan pokok

1. **Anisotropi galat** — $\sigma_{\text{kedalaman}}/\sigma_{\text{lateral}} = z/h$, tidak bergantung pada focal length maupun resolusi.
2. **Degenerasi kalibrasi** — dari marka jalan saja, $f$, $h$, dan lebar lajur $w$ tidak teridentifikasi terpisah. Yang terukur hanya $f\theta$, $fh$, $fw$, dan $w/h$. Diperlukan satu anchor metrik.
3. **Batas pengukuran** — lebar dan tinggi layak pada 18–30 m; panjang tidak layak bila sumbu optik sejajar jalan.

## Skrip

Tidak ada dependensi eksternal selain Node.js dan `ffmpeg`.

### Verifikasi teori

| Berkas | Fungsi |
|---|---|
| `verify_geometry.mjs` | Verifikasi numerik proyeksi, kalibrasi VP, rekonstruksi, dan Jacobian |
| `worked_example.mjs` | Contoh numerik lengkap (laporan riset §8) |
| `sensitivity_check.mjs` | Sensitivitas per sumbu |
| `degeneracy.mjs` | Uji degenerasi 1-parameter |
| `check_claims.mjs` | Verifikasi klaim angka |

### Pipeline kalibrasi

| Berkas | Fungsi |
|---|---|
| `vpfit.mjs` | Estimasi vanishing point dari orientasi dash |
| `scan.mjs` | Penyapuan profil luma sepanjang garis lajur |
| `dash3.mjs` | Ekstraksi dash dengan tepi sub-piksel (final) |
| `calib3.mjs` | Fitting model kamera + kovarians (final) |
| `anchor.mjs` | Fitting dengan lebar lajur dipaku |
| `annotate.mjs` | Utilitas overlay validasi |

Berkas `marks.mjs`, `blobs.mjs`, `dashes.mjs`, `dash2.mjs`, `lines.mjs`, `lines2.mjs`, `calib.mjs`, `calib2.mjs`, `sens.mjs`, dan `measure.mjs` adalah iterasi yang mendahului versi final — disimpan sebagai catatan proses.

## Artefak

| Berkas | Isi |
|---|---|
| `frames/median.png` | Latar median-temporal (rata-rata, revisi 1) |
| `frames/median2.png` | Latar median-temporal sejati (revisi 2) |
| `frames/ann2.png` | Overlay validasi: garis lajur dan pusat dash prediksi |
| `frames/truck2.png` | Crop objek acuan dengan grid |
| `frames/*.json` | Hasil deteksi dan parameter |

## Catatan

Berkas video sumber (`recording cawang.mp4`, 179 MB) **tidak** disertakan dalam repositori. Ukurannya melampaui batas praktis git, dan rekaman berisi citra lalu lintas yang dapat diidentifikasi.

Seluruh angka dapat direproduksi dari video tersebut dengan perintah pada lampiran `KALIBRASI-CCTV-CAWANG-REV2.md`.
