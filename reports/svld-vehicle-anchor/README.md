# SVLD: Bisakah Kendaraan Well-Known Jadi Anchor?

**Tanggal:** 20 November 2026  
**Pertanyaan:** bisakah memilih kendaraan yang modelnya dikenal di SVLD, lalu memakai dimensi pabrikannya sebagai anchor skala?

---

## 1. Ringkasan

1. **Secara konsep bisa**, tetapi **bukan dengan anotasi SVLD**. `veh_size`, `vertex3d`, dan `vertex2d` dibangun dari box yang sama; memakainya sebagai anchor adalah sirkular.
2. **SVLD tidak punya kontainer 20/40 ft** yang bisa dipakai seperti Cawang. Truck L hanya 5,2 / 4,8 / 20,0 / 7,4 / 14,0 m; bus 12,6 m.
3. Saya menemukan bus dengan model terbaca: **Higer KLQ6129 (kelas 12 m)** di `real_scene_cam0_003368` (rute 313). `veh_size` SVLD memberinya **12,6 × 2,75 × 2,8 m**; kelas 12 m biasanya **≈12,0 × 2,55 × 3,2 m**. Selisih indikatif: L **+5%**, W **+7,8%**, H **−12,5%**.
4. Artinya: **label SVLD bukan dimensi bus itu**. Memakai bus ini dari anotasi SVLD akan mewarisi galat preset, bukan mengukur kendaraan nyata.
5. Untuk uji yang sah: pilih model persis, ambil dimensi dari datasheet pabrikan, lalu **anotasi manual 8 sudut/5 titik** di citra — bukan `vertex2d` SVLD.

---

## 2. Bukti kandidat

| Hal | Nilai |
|---|---|
| Gambar | `SVLD-3D-TRAINVAL-SCENE-D/DATA2021/JPEGImages/real_scene_cam0_003368.jpg` |
| Kendaraan | Bus kota, rute 313, livery putih, logo **HIGER** |
| Teks model | Terbaca mengarah ke **KLQ6129GAHEVC** (sebagian; perlu verifikasi) |
| `veh_size` SVLD | 12,6 × 2,75 × 2,8 m |
| Kelas pabrikan 12 m (tipikal) | ≈12,0 × 2,55 × 3,2 m |
| Selisih indikatif | L +5,0%; W +7,8%; H −12,5% |

Catatan: angka pabrikan adalah **kelas tipikal 12 m**, bukan datasheet resmi varian hybrid. Verifikasi model/year tetap diperlukan. Kalau model sebenarnya KLQ6109 (10,9 m), selisih L bahkan lebih besar.

---

## 3. Mengapa anotasi SVLD tidak bisa jadi anchor

- `vertex3d` adalah box 3D di dunia; `vertex2d` adalah proyeksinya; `veh_size` adalah dimensi box itu.
- Reproyeksi 8 sudut SVLD konsisten **<1,1 px** karena ketiganya berasal dari box yang sama.
- Fit 8 sudut akan mengembalikan `veh_size` hampir tepat — itu **self-consistency**, bukan pengukuran kendaraan nyata.
- Untuk anchor, kita butuh titik 2D yang **independen** dari box 3D: klik manual pada bodi kendaraan di citra.

---

## 4. Uji yang sah (kalau mau dilanjutkan)

1. Pilih **satu model** dengan teks/model yang jelas; minimal 3 instance.
2. Cari **datasheet pabrikan** untuk model/year itu (length/width/height).
3. Anotasi manual 8 sudut bodi atau 5 titik (4 kontak tanah + atap) di citra; jangan pakai `vertex2d`.
4. Pakai kalibrasi GT SVLD untuk memproyeksikan/measure; bandingkan dengan datasheet.
5. Laporkan galat per instance dan variasi model/year.
6. Gate: jika 3–5 instance konsisten **<5%**, model itu layak jadi **weak anchor**; jika >10%, tidak.

Perkiraan realistis: **3–5%** untuk model yang benar dan anotasi rapi; tidak sebaik kontainer 20 ft Cawang (**0,2%**).

---

## 5. Rekomendasi

- **Jangan pakai kendaraan SVLD dari anotasi dataset sebagai anchor.** Itu sirkular.
- **Gunakan kontainer 20 ft** (Cawang) sebagai anchor fisik utama; SVLD tidak punya kontainer standar.
- SVLD tetap berguna untuk: kalibrasi GT, geometri, VP, dan uji metode.
- Kalau ingin menguji ide kendaraan well-known, pilih **kendaraan fleet dengan dimensi terdokumentasi** (bus operator tertentu) dan anotasi manual; bukan model umum yang tidak pasti.
- Bus Higer di atas bisa menjadi **studi kasus**: preset 12,6 m vs kelas 12 m menunjukkan `veh_size` bukan GT fisik.

---

## 6. Berkas

- `out/svld_vp/bus_front_zoom.jpg` — crop pembesaran model bus (tidak disertakan di repo).
- Gambar asli: `SVLD-3D-TRAINVAL-SCENE-D/DATA2021/JPEGImages/real_scene_cam0_003368.jpg`.
- Anotasi: `SVLD-3D-TRAINVAL-SCENE-D/DATA2021/Annotations/real_scene_cam0_003368.xml`.

---

## 7. Batas

- Model bus terbaca sebagian; datasheet resmi belum diverifikasi.
- Angka pabrikan di atas adalah kelas tipikal, bukan pengukuran unit.
- Tidak ada anotasi manual independen dalam uji ini; ini baru **feasibility check**.
- SVLD tidak punya kontainer 20/40 ft, jadi tidak ada physical standard seperti Cawang.
- `veh_size` preset; jangan dipakai untuk klaim akurasi fisik.
