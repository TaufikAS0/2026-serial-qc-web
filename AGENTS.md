# Instruksi AI

Baca `04_Dokumen/IMPLEMENTATION_PROMPT.md` dan `04_Dokumen/STATUS.md` sebelum implementasi.

- Scope aktif: penguji protokol serial umum melalui RS232/RS485, layanan web lokal Windows. Compact QC adalah profil opsional, bukan baseline wajib aplikasi.
- User meminta dokumentasi siap lanjut; implementasi dilakukan AI berikutnya di laptop pengguna. Jangan mengklaim launcher/service sudah tersedia.
- Audit branch/status/remote; pertahankan pekerjaan orang lain. Gunakan feature branch dari develop yang sudah memuat revisi scope; jika belum merge, lanjut dari branch revisi aktif dan jelaskan dependensi PR.
- Push branch dan ajukan PR ke develop, jangan merge otomatis atau push langsung main/develop.
- RS232/RS485 bukan format pesan. Setiap PASS membutuhkan aturan test dan bukti; raw monitor hanya menampilkan data.
- Tidak ada ketergantungan inti pada ESP, IP device, API arm, GPIO, MCP, atau jumlah dua tag. Integrasi spesifik harus diisolasi.
- Gunakan localhost/loopback, satu pemilik port, konfigurasi portable, bounded logs dan retention. Jangan menjalankan payload serial otomatis setelah reboot/crash.
- Aktifkan startup/recovery secara transparan dengan installer, status dan uninstaller. Jangan ubah sleep/power policy diam-diam.
- Jangan commit credentials, konfigurasi mesin, atau data produksi. Profil JSON tidak mengeksekusi script arbitrary.
- Mock transport dilabel SIMULASI; software tests bukan hardware acceptance.
- Update STATUS.md setiap checkpoint, termasuk test, blocker, dan next step.
- Reuse source hanya setelah audit lisensi/provenance/kompatibilitas. Jangan clone seluruh firmware ke core aplikasi.
- Tidak upload firmware atau mengubah repository firmware. Jika ada kebutuhan perubahan firmware, laporkan secara terpisah.
