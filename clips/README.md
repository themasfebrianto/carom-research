# Klip Bukti Video

Klip pendek dari dua rekaman Cawang. Semua klip video utama dipotong dengan **`-c copy`** — tidak ada re-encode, jadi pikselnya identik dengan sumber.

## Isi

| Berkas | Sumber | Interval | Isi |
|---|---|---|---|
| `cawang_032_kandidat.mp4` | `recording cawang.mp4` | 30–34 s | Kandidat 20 ft / box truck pada t=32 |
| `cawang_086_sinkor.mp4` | `recording cawang.mp4` | 84–88 s | Truk SINKOR; kontainer 40/45 ft pada t=86 |
| `cawang_247_20ft-tema.mp4` | `recording cawang.mp4` | 245–249 s | Kontainer 20 ft TEMA pada t=247; validasi 6,046 m vs 6,058 m |
| `cawang_431_truk-panjang.mp4` | `recording cawang.mp4` | 429–433 s | Truk panjang pada t=431 |
| `cawang_567_truk-panjang.mp4` | `recording cawang.mp4` | 565–569 s | Truk panjang pada t=567 |
| `cawang_578_40ft.mp4` | `recording cawang.mp4` | 576–580 s | Kontainer 40 ft pada t=578 |
| `audit_16-15-44_full-480p.mp4` | `16-15-44.mp4` | 0–600 s | Substream 480×360 utuh; bahan `AUDIT-16-15-44.md` |

Total: **15,42 MB** (6 klip utama 7,18 MB + substream 8,24 MB).

## Mengapa klip, bukan video penuh

Sumber utama: 1280×720, 25 fps, 600 s, H.264 Constrained Baseline, 2,5 Mbps, **187,8 MB**.

Uji pada segmen 20 detik (t=240–260):

| Cara | Ukuran setara 600 s | VMAF | Catatan |
|---|---:|---:|---|
| `-c copy` klip 4 s | **~6 MB per klip** | identik | tanpa re-encode |
| Lossless x264 (`-qp 0`) | **~1,16 GB** | identik | 6× lebih besar dari sumber |
| x264 CRF 23 | ~222 MB | 99,37 | lebih besar dari sumber |
| x264 CRF 30 | ~145 MB | 92,84 | masih >100 MB |
| x264 CRF 32 | ~115 MB | 89,12 | masih >100 MB |
| x264 CRF 34 | ~87 MB | 84,61 | di bawah 100 MB, tetapi kualitas turun |

Jadi **tidak ada re-encode yang lebih kecil tanpa penurunan kualitas**. Satu-satunya cara mempertahankan piksel sekaligus mengecilkan berkas adalah memotong segmen yang relevan.

## Verifikasi

Dari dalam folder `clips/`:

```bash
sha256sum -c SHA256SUMS
```

Di PowerShell:

```powershell
Get-FileHash clips\*.mp4 -Algorithm SHA256
```

Bandingkan dengan `SHA256SUMS`.

## Catatan

- Rekaman penuh `recording cawang.mp4` (187,8 MB) **tidak** disertakan; hanya segmen bukti.
- Substream `16-15-44.mp4` disertakan utuh karena ukurannya hanya 8,2 MB dan seluruh rekaman itulah yang diaudit.
- Kedua rekaman berisi citra lalu lintas yang dapat diidentifikasi. Jaga repo tetap privat atau batasi aksesnya; jangan unggah ulang ke layanan publik.
- Indeks klip ini juga dipakai di `README.md`, `HASIL-TIMEPASS-CAWANG.md`, dan `AUDIT-16-15-44.md`.
