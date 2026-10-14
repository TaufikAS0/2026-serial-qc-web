# Prompt implementasi untuk AI berikutnya

Kamu bertugas menyelesaikan aplikasi web lokal untuk Quality Control komunikasi RS232 dan RS485 pada hardware Compact QC Tester saya. Kerjakan sampai bisa dijalankan, bukan hanya desain atau mockup. Mulai dengan source yang tersedia dan gunakan kembali implementasi yang sudah benar.

## 1. Konteks dan sumber kebenaran

Repository aplikasi baru ini adalah tempat pekerjaanmu. Referensi firmware: https://github.com/TaufikAS0/compact-qc-tester-v2-r1, branch `feature/qc-operator-ota`. Baseline firmware v1.5.0 adalah `fa0624ea3d979f2a87ff3db118a46c4ad6ca0387`; checkpoint dokumentasi `7481e0af5b6721083e6701bb8cf311ec0137ec9d`.

Verifikasi kondisi terbaru; jangan menganggap main sudah memiliki fitur branch tersebut. Jika source bergerak, catat commit yang digunakan dan alasan memilihnya. Audit ketentuan reuse dan provenance sebelum mengambil file. Jangan menyalin secret atau seluruh firmware ke aplikasi ini.

Cari dan baca pada repo referensi:
- `tools/laptop-qc/`, termasuk `server.py` dan pendukungnya.
- `Start-Laptop-QC.ps1`.
- Source protokol serial QC, routing RS232/RS485, dan Modbus.
- Tests protokol/worker yang sudah ada.
- `04_Dokumen/QC_OPERATOR_GUIDE.md`, README, AGENTS, serta checkpoint `ai/`.

Path yang belum ditemukan harus dicari, bukan diasumsikan. Clone referensi secara terpisah atau dalam `_references/` yang di-ignore; jangan membuat gitlink/nested repo terlacak. Source aplikasi hasil reuse diletakkan secara normal di repo ini dengan attribution yang sesuai.

Dashboard preview ESP sebelumnya menggunakan localhost:8769; aplikasi laptop ditujukan localhost:8770. Keduanya berbeda fungsi. Alamat device dan port COM tidak tetap: teknisi harus bisa mengubahnya.

## 2. Tujuan operator

Teknisi menjalankan launcher, membuka web, memasang USB–RS232 atau USB–RS485, memilih COM/mode, menghubungkan device, menekan Mulai QC, lalu melihat hasil dan menyimpan laporan. Aplikasi harus bisa menguji banyak device berturut-turut tanpa restart server.

## 3. Arsitektur

Utamakan melanjutkan backend Python yang sudah tersedia dengan pyserial, serta frontend yang disajikan backend lokal. Browser adalah antarmuka; backend menangani COM, parser, pengujian, dan penyimpanan. Jangan menduplikasi protokol pada frontend/backend.

Default bind loopback, frontend/API same-origin. Lindungi endpoint perubahan state dari request lintas origin yang tidak diizinkan. Aplikasi harus berjalan tanpa internet setelah dependensi terpasang; hindari CDN runtime.

Pisahkan serial transport, encoder/parser, mesin pengujian, integrasi HTTP ESP, penyimpanan/export, dan frontend. Gunakan path relatif dan konfigurasi portable. Jangan mensyaratkan folder atau username laptop pembuat.

## 4. Hardware dan wiring

Mapping yang diberikan: ESP32 RX GPIO4, TX GPIO5; selector MCP2A2 HIGH/ON untuk RS232 dan LOW/OFF untuk RS485. RS485 PCB memiliki arah otomatis tanpa DE/RE. Cocokkan dengan source sebelum mengirim perintah.

Gunakan USB–RS232 untuk port RS232, bukan USB–TTL. Diagram operator: TX adapter ke RX device, RX adapter ke TX device, signal ground. Jangan mengarang nomor DB9.

Untuk RS485, dokumentasikan pasangan diferensial berdasarkan polaritas/datasheet adapter dan board; label A/B antarvendor tidak boleh diasumsikan sama. Jelaskan referensi ground, terminasi, dan bias sesuai fixture/topologi.

Default QC 9600 baud, 8N1, configurable sesuai dukungan firmware. Ini profil awal, bukan klaim semua RS232 wajib memakai konfigurasi itu.

## 5. QC RS232

Sebelum coding, temukan dan dokumentasikan kontrak aktual: magic/header, versi, tipe pesan, panjang, run ID, sequence, payload, CRC, endianness, ACK, timeout, akhir sesi, endpoint arm/stop/heartbeat/result. Jangan menciptakan format atau endpoint pengganti tanpa bukti kebutuhan.

Default 100 transaksi dan timeout mengikuti firmware. Alur:
1. Validasi konfigurasi/port dan identitas/kompatibilitas firmware.
2. Buka serial eksklusif dan siapkan sesi QC device.
3. Kirim paket melalui adapter dan kabel RS232.
4. Validasi response, transformasi payload, CRC, run ID, sequence, dan ACK sesuai protokol.
5. Rekonsiliasi hasil laptop dengan device, lalu cleanup resource.

HTTP/Wi-Fi boleh untuk konfigurasi/arm/heartbeat/result; bukti QC serial harus berasal dari data serial fisik. HTTP sukses atau COM berhasil dibuka bukan PASS. Validasi transformasi response jika protokol menyediakannya agar local echo tidak menjadi PASS palsu.

## 6. QC RS485

Sediakan tes paket dua arah yang setara pada jalur RS485. Reuse protokol QC firmware jika memang didukung, setelah konfirmasi source.

Tangani half-duplex, arah otomatis, local echo, response parsial, beberapa frame dalam satu read, timeout, frame rusak, dan data sesi lama. RS232/RS485/Modbus tidak boleh berjalan bersamaan pada UART/port yang sama.

## 7. Fixture slave Modbus untuk dua tag

Device memiliki mode master Modbus dua tag independen. Laptop harus menjadi slave/server melalui USB–RS485 untuk mengujinya; jangan menjadikan keduanya master pada bus yang sama.

Mode Simulator Slave Modbus menyediakan:
- Slave ID dan serial settings configurable.
- FC01 Read Coils, FC02 Read Discrete Inputs, FC03 Read Holding Registers, FC04 Read Input Registers.
- Peta alamat/nilai yang bisa diubah teknisi.
- Dua preset tag independen agar mudah dicocokkan dengan dashboard device.
- Unsigned, signed, float32 sesuai batas firmware dan pilihan word order nilai dua register.
- Raw register/bit dan nilai hasil interpretasi.

Alamat protokol zero-based adalah sumber kebenaran. Jika menampilkan 40001 dan sejenisnya, jelaskan konversi eksplisit. Tampilkan request masuk, slave/function/alamat/jumlah, response, expected value, timestamp, exception/error.

Response terkirim dari laptop belum membuktikan device menerima/menafsirkan nilai. QC end-to-end harus membaca hasil device lewat API nyata atau meminta konfirmasi operator atas nilai yang tampil pada device. Dua tag sesuai menghasilkan PASS; yang belum diuji tidak PASS.

Pisahkan fixture Modbus dari protokol paket QC custom. Jangan menamakan protokol custom sebagai Modbus. Mode fixture adalah alat pengujian nyata dengan nilai sintetis yang diketahui; bedakan dari mock transport tanpa hardware.

## 8. Hasil QC

Status: BELUM DIUJI, BERJALAN, PASS, FAIL, DIBATALKAN/INCOMPLETE, ERROR SETUP.

Tes paket PASS hanya jika semua transaksi wajib valid dan hasil device cocok dengan run laptop. Timeout, CRC/payload/sequence salah dan kegagalan transaksi harus tercatat. Retry tidak menghapus kegagalan; default nol error berarti berhasil setelah retry tidak mengubah run menjadi PASS.

Stop bukan PASS. Port tidak tersedia sebelum mulai adalah ERROR SETUP, bukan bukti otomatis kerusakan hardware. Bedakan gangguan jaringan kontrol HTTP dari kegagalan serial; jika bukti akhir tidak lengkap jangan mengarang hardware FAIL atau PASS. Hasil run sebelumnya tidak boleh terbawa ke device baru.

Modbus membedakan protokol valid, response terkirim, dan nilai end-to-end terkonfirmasi. Sediakan Sesuai/Tidak sesuai bila dibutuhkan; hasil per tag dan keseluruhan terlihat jelas.

## 9. Antarmuka Bahasa Indonesia

Halaman/panel: Koneksi, QC RS232, QC RS485, Simulator Slave Modbus, Riwayat/Export.

Koneksi: daftar COM/deskripsi adapter, Refresh, mode, baud/format yang didukung, IP/URL device editable, Cek koneksi, serial number, versi firmware, waktu build jika tersedia. Jangan hardcode IP/COM aktif dari sesi lama.

Kontrol: Mulai QC, Stop, Uji ulang, Device berikutnya/sesi baru, jumlah paket dan timeout sesuai batas firmware.

Saat run: progress, transaksi valid/target, error/timeout, durasi, round-trip statistics jika dapat diukur, TX/RX ringkas dan detail hex opsional, alasan gagal yang mudah dibaca.

PASS besar hijau, FAIL besar merah, teks/ikon selain warna. Hasil ada di panel tes aktif, bukan hanya ringkasan. Raw JSON bukan UI utama operator. Kunci perubahan config yang tidak aman selama run, Stop tetap tersedia. Refresh browser tidak boleh membuat run kedua.

## 10. Ketahanan

Tangani USB dicabut, COM busy/berubah, device reboot, IP salah, API bukan JSON, firmware incompatible, klik Mulai ganda, dua tab, buffer lama, partial/combined/corrupt/stale frames, sequence duplikat, Stop saat menunggu, dan shutdown saat port terbuka.

Satu pemilik port dan satu active run, run ID unik, cleanup pada sukses/gagal/cancel/exception. Simpan hasil bertahap. Run yang terputus ditandai INCOMPLETE setelah restart. Riwayat tetap tersedia untuk device berikutnya.

## 11. Riwayat dan export

CSV Excel dan JSON berisi run ID, waktu/zona waktu, serial device, versi/build firmware jika tersedia, versi aplikasi, mode, COM/adapter, serial settings, target/berhasil/error/timeout/retry, durasi/latency jika ada, hasil/alasan, hasil laptop dan device terpisah, detail tag, catatan operator opsional.

Identitas yang tidak terbaca adalah unknown. Gunakan UTF-8 yang terbaca Excel, escaping benar, dan pencegahan formula injection kolom teks. Jangan menyertakan token/password. Data produksi lokal di-ignore Git.

## 12. Tests dan bukti

Uji golden frames dari firmware, CRC/payload/run/sequence/ACK, partial/combined/corrupt/stale/local echo, timeout/cancel/COM busy/disconnect, PASS gate, single owner, Modbus exception/response, dua tag/endianness, frontend dengan elemen/API nyata, export/riwayat.

Sediakan mock transport untuk development dengan label SIMULASI. Mock tidak boleh menghasilkan laporan hardware PASS nyata. Jika hardware belum tersedia, selesaikan source/automated tests dan tandai hardware acceptance belum dilakukan.

## 13. Deliverable

Source lengkap, launcher Windows, dependency/setup, README, wiring, kontrak serial/API berdasarkan kode aktual, panduan operator ketiga mode, tests/hasil, contoh export simulasi, checklist hardware, dan checkpoint yang cukup untuk AI berikutnya.

## 14. Batas dan cara bekerja

Fokus aplikasi laptop; firmware tidak diubah jika kontrak cukup. Jika blocker firmware, tunjukkan file/masalah/perubahan minimal. Jangan diam-diam mengganti protokol atau upload firmware; tim user melakukan upload.

Baca AGENTS/aturan workspace, audit status/branch/remote, pertahankan perubahan orang lain, gunakan feature branch dari develop dan PR; jangan merge otomatis atau push main.

Mulai dengan ringkasan apa yang tersedia, gap, kontrak yang ditemukan, dan urutan implementasi. Lalu langsung kerjakan sampai deliverable terpenuhi. Perbarui STATUS.md setiap checkpoint, jangan berhenti pada rencana/mockup.
