# Checkpoint — 2026-10-14 UTC+7

## Scope aktif

User mengoreksi scope menjadi aplikasi umum test data protokol RS232/RS485 yang selalu tersedia di laptop. Repo diganti dari 2026-compact-serial-qc-web menjadi 2026-serial-qc-web; folder lokal mengikuti slug. Revisi docs ada di feature/general-serial-protocol-handoff, PR ke develop. Prompt lama pada commit bootstrap bukan scope aktif.

## Status jujur

Dokumentasi saja. Tidak ada source aplikasi, installer, autostart, backend berjalan, atau test hardware dalam repo ini. AI lain di laptop pengguna yang akan mengimplementasikan sisanya. Tidak mengubah firmware/perangkat atau power settings.

## Checklist AI berikutnya

- [x] Prompt generik; Compact hanya integrasi opsional.
- [x] Spesifikasi backend background, autostart login, restart, stop/status/uninstall, batas sleep.
- [ ] Core transport dan port ownership, terminal ASCII/HEX.
- [ ] Modbus master dan slave simulator.
- [ ] Profil/schema dan scenario/assertion engine.
- [ ] UI Bahasa Indonesia dan hasil jelas.
- [ ] Persistence, CSV/JSON, log retention.
- [ ] Windows launcher dan lifecycle/autostart/recovery.
- [ ] Tests, simulated fixtures, real browser dan hardware acceptance.
- [ ] Panduan pengguna dan checkpoint implementasi.
- [ ] Opsional: profil Compact dari reference setelah core selesai.

Langkah berikutnya: gunakan branch scope aktif (atau develop setelah PR digabung), audit dokumen, mulai implementasi generik. Jangan menunggu firmware ESP/IP tertentu. Pelihara Gitflow/PR dan catat exact test evidence.

## Aturan yang dibaca pada bootstrap

Firmware_AI_Vault_Home, Rules_Nama_dan_Folder_Workspace, Rules_Firmware_Standar, Rules_GitHub_Gitflow, Rules_Kredensial_WiFi, WiFi_HuaweiJIN, Rules_Versioning, Rules_Change_Notifications dan gitflow-guardian. Semua perubahan kini dokumentasi software laptop; versi/build firmware, pin/API/NVS tidak berubah. Profil lab STA HuaweiJIN/AP12345678 tidak menjadi persyaratan koneksi aplikasi generik; tidak ada migrasi NVS.
