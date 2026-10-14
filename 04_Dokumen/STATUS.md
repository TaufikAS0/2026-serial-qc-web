# Checkpoint pekerjaan

Tanggal: 2026-10-14 (UTC+7).

## Status sebenarnya

Dokumentasi handoff disiapkan atas permintaan user. Belum ada kode aplikasi, dependensi terpasang, launcher, build, simulasi, atau pengujian hardware di repository baru ini. Implementasi penguji lama berada di repository firmware; belum dipindahkan.

## Langkah pertama AI berikutnya

Audit source penguji lama dan firmware pada baseline README. Buat tabel kontrak API/frame dari kode nyata, identifikasi gap, lalu implementasikan aplikasi di feature branch repository ini. Gunakan path relatif agar dapat dikerjakan di laptop lain.

## Checklist

- [x] Prompt implementasi dan referensi baseline.
- [x] Aturan handoff, Gitflow, dan status jujur.
- [ ] Audit/reuse source penguji lama beserta provenance.
- [ ] Dokumentasikan kontrak frame/API aktual dan golden vectors.
- [ ] Backend serial, kepemilikan port, worker, cancellation.
- [ ] UI koneksi, QC RS232, QC RS485, status lokal jelas.
- [ ] Simulator slave Modbus RTU untuk master dua tag pada device.
- [ ] Riwayat, recovery run terputus, export CSV/JSON.
- [ ] Launcher Windows dan setup dependency.
- [ ] Automated tests/parser/error paths dan UI nyata.
- [ ] Panduan operator/wiring dan contoh export simulasi.
- [ ] Uji hardware dengan adapter dan device; jangan tandai selesai tanpa bukti.

## Fakta dan unknowns

Firmware referensi v1.5.0 pernah lulus build/software tests di pekerjaan sebelumnya. Hal itu tidak membuktikan aplikasi baru ini tersedia atau hardware sudah menerima firmware. Versi firmware terpasang, alamat IP, dan port COM saat implementasi harus dicek kembali.

## Catatan aturan bootstrap

Dibaca dari vault firmware workspace: Firmware_AI_Vault_Home.md, Rules_Nama_dan_Folder_Workspace.md, Rules_Firmware_Standar.md, Rules_GitHub_Gitflow.md, Rules_Kredensial_WiFi.md, WiFi_HuaweiJIN.md, Rules_Versioning.md, Rules_Change_Notifications.md; serta skill gitflow-guardian.

Ini proyek software laptop/dokumentasi: tidak ada perubahan versi firmware, build, pin, API perangkat, atau NVS. Profil firmware lab yang dibaca adalah STA HuaweiJIN dan AP default 12345678; tidak ada konfigurasi Wi-Fi/NVS yang diterapkan oleh bootstrap ini.
