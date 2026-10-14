# Profil v1 dan kontrak protokol

Lihat [JSON Schema](profile.schema.json), [raw PING](../examples/raw-ping.json), dan [Modbus read](../examples/modbus-read.json). Backend `profiles.validate` memeriksa struktur dan aturan semantik; schema untuk editor/tool eksternal. Tidak ada eksekusi script, regex, plugin checksum, atau write Modbus dari profil.

Nama, `version: 1`, `protocol: raw|modbus`, dan `steps` wajib. Fixture default MOCK. Untuk hardware, salin profil, beri nama sesuai DUT, ubah fixture REAL, dan sesuaikan kontrak pesan DUT. Pilih COM di Koneksi; COM tidak disimpan dalam profil portable. `serial` opsional berisi baud/bits/parity/stop/flow/interface; run ditolak jika settings berbeda dari koneksi. `notes` opsional untuk kontrak fixture.

Setiap langkah memiliki timeout 0.05–30 detik dan minimal satu assertion. Repeats 1–1000; total maksimum 10000 langkah. Tidak ada retry tersembunyi; setiap error tetap tercatat. Interval antar langkah 0.01–60 detik. PASS hanya jika semua langkah wajib selesai dan nol error. Stop/unplug/restart menghasilkan INCOMPLETE. Kesalahan profil/koneksi sebelum mulai adalah ERROR SETUP pada notifikasi, bukan diagnosis hardware rusak.

## Raw

`format` ASCII atau HEX; payload 1–4096 bytes termasuk ending. Encoding ascii/utf-8/latin-1, ending none/CR/LF/CRLF. HEX harus pasangan byte valid. Framing menggunakan `length` eksplisit, `delimiter_hex`, atau idle gap (`idle_ms`, default 50); prioritas length lalu delimiter lalu idle. Bytes ekstra tetap masuk assertion, tidak dibuang agar mismatch terlihat. Profile harus sesuai framing DUT. Data unsolicited/noise dapat menyebabkan FAIL, bukan dipilih diam-diam sebagai PASS.

Assertions `exact`, `prefix`, `contains` membandingkan `hex`; `length` membandingkan `value`. Exact paling kuat jika format DUT pasti. Prefix/contains/length hanya membuktikan aturan yang dipilih, bukan kebenaran semua isi paket. TX yang sama persis dengan RX ditolak pada REAL/MOCK untuk mencegah local echo; hanya fixture LOOPBACK boleh menerimanya. LOOPBACK membuktikan jalur adapter/kabel, tidak DUT. Tidak menyisipkan sequence ID ke protokol yang tidak mendukungnya.

## Modbus read

`unit` 1–247; `function` 1/2/3/4; `address` zero-based; `count` 1–2000 bits untuk FC01/02 atau 1–125 register untuk FC03/04. Batas alamat akhir 65536. FC01/02 memakai `type: bits`; FC03/04 uint16/int16 (count 1), uint32/int32/float32 (count 2). Tag dinamis tersedia pada UI master. `byte_order` membalik byte dalam setiap word; `word_order` membalik dua word untuk data 32-bit. Decode kemudian `value * scale + offset`. NaN/Infinity ditolak.

Range: `{"kind":"range","min":99,"max":101}`. Tolerance: `{"kind":"tolerance","target":100,"tolerance":1}`. Nilai adalah decoded/scaled scalar; bits dapat memakai assertion frame bytes/panjang. CRC, unit, fungsi, byte count, exception, panjang, padding bits, dan batas read selalu diverifikasi. Raw registers, TX/RX HEX, latency dan error tersimpan. Notasi 40001 tidak diterima sebagai alamat offset otomatis.

Slave maps JSON: `{"unit":1,"maps":{"1":{"0":1},"2":{"0":0},"3":{"0":100},"4":{"0":200}}}`. FC01 coils, FC02 discrete inputs, FC03 holding, FC04 input. Maksimum 2000 alamat/map; keys alamat desimal zero-based; bits 0/1, registers 0..65535. Import/export preset di UI. Alamat di luar map → exception 02; count tidak valid → 03; fungsi unsupported → 01. CRC rusak dibuang. Unit lain/broadcast tidak dibalas. MOCK inject pada panel slave memungkinkan request masuk sintetis; ini bukan serial fisik.

## Report dan batas

CSV UTF-8 BOM + quoting + perlindungan formula Excel dan JSON dapat diexport dari Riwayat. Waktu disimpan ISO UTC, UI Asia/Jakarta. Report menyimpan profil/version, serial, fixture, identity manual/unknown, assertions, TX/RX, latency, error, status dan policy nol retry. Riwayat maksimum 200 run / 64 MB; detail tiap run maksimum 500 langkah / 1 MB. Field `truncated_results` menyatakan detail yang dibuang; completed/errors/target tetap seluruh run. Export sebelum retention untuk arsip lengkap; aplikasi tidak menjanjikan menyimpan log produksi tanpa batas.

Referensi resmi: [Modbus Application Protocol v1.1b3](https://www.modbus.org/file/secure/modbusprotocolspecification.pdf), [Serial Line v1.02](https://www.modbus.org/file/secure/modbusoverserial.pdf), [pyserial API](https://pyserial.readthedocs.io/en/latest/pyserial_api.html). Codec implementasi asli berdasarkan kontrak ini; tidak menyalin firmware atau core Compact.
