# Instruksi AI

Mulai dari `04_Dokumen/IMPLEMENTATION_PROMPT.md` dan `04_Dokumen/STATUS.md`.

- Repository ini adalah software penguji laptop. User meminta AI lain melanjutkan implementasi di laptopnya; bootstrap ini hanya dokumentasi.
- Audit status/branch/remote sebelum mengubah file. Pertahankan perubahan orang lain.
- Baseline protokol berasal dari source firmware yang ditautkan README. Endpoint, frame, dan kemampuan harus diverifikasi dari source, bukan dikarang.
- Reuse implementasi laptop terdahulu setelah audit kompatibilitas dan ketentuan reuse. Catat commit upstream dan file yang diambil. Jangan menyalin seluruh firmware atau secret.
- Buat feature branch dari develop. Push feature branch dan buka PR ke develop setelah verifikasi; jangan merge otomatis atau push langsung main/develop setelah bootstrap.
- Default aplikasi lokal loopback; jangan hardcode path mesin, port COM, atau IP perangkat.
- Pisahkan hasil simulasi, software tests, dan hasil hardware nyata. Tidak ada hardware PASS tanpa bukti.
- Jangan upload firmware ke perangkat. Jika ada blocker firmware, dokumentasikan perubahan minimal yang diperlukan; jangan diam-diam mengubah kontrak.
- Perbarui STATUS.md dengan perubahan, tes, commit, blocker, dan langkah berikutnya setiap checkpoint.
- Tidak ada kredensial privat dalam Git/log/export. Data lokal/hasil produksi harus di-ignore.
- Jika tugas meluas ke firmware, baca AGENTS dan aturan firmware/versioning pada repository firmware terlebih dahulu. Aturan lab bukan izin menerapkan akses tanpa autentikasi pada semua proyek.
