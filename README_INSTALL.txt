LOGBOOK DERMAGA JTI - SCRIPT LAPTOP WINDOWS
===========================================

Script ini mengisi logbook Dermaga JTI otomatis dari laptop kamu.
Kegiatan tetap KAMU yang isi lewat popup; script TIDAK PERNAH
mengarang kegiatan.

Kenapa perlu script: browser Muse tidak bisa memberi izin lokasi,
jadi tombol Simpan selalu ditolak Dermaga. Script ini membuka
browser sendiri dengan lokasi kantor Denpasar (Renon,
-8.67714, 115.23964), jadi cek lokasi Dermaga lolos.


ISI FOLDER
----------
  logbook_dermaga.py   Script utama.
  run_logbook.bat      Pembungkus untuk Task Scheduler (cara manual).
  logbook_config.json  Dibuat otomatis saat pertama jalan.
                       Isi USERNAME saja, JANGAN tulis password.
  logbook_run.log      Catatan tiap jalan (berhasil/gagal).
                       Tidak berisi password.


INSTALL (SEKALI SAJA)
---------------------
1. Install Python 3.11+ dari https://python.org
   Saat install, CENTANG "Add python.exe to PATH".

2. Salin folder ini ke laptop, misal:
     C:\logbook-dermaga\

3. Buka Command Prompt di folder itu, jalankan:
     python logbook_dermaga.py

   Saat jalan pertama, script akan menawarkan:
   - Install Playwright + Chromium  -> jawab Ya (wajib; Tidak = berhenti).
   - Install keyring                -> jawab Ya (opsional, untuk
                                       menyimpan password).
   - Buat task Task Scheduler       -> jawab Ya (Senin-Jumat 18:00).

   Install manual (kalau otomatis gagal):
     python -m pip install playwright keyring
     python -m playwright install chromium

4. Script membuat logbook_config.json lalu berhenti.
   Isi username Dermaga kamu di file itu, lalu jalankan lagi:
     python logbook_dermaga.py


PEMAKAIAN
---------
1. Popup "Kegiatan hari ini apa?" -> isi, tekan OK.
2. Jendela password -> ketik password Dermaga.
   - Centang "Simpan password (Windows Credential Manager)"
     supaya besok tidak ditanya lagi.
   - Tekan "Simpan Password & Lanjut", atau "Batal" untuk berhenti.
   Password disimpan di Windows Credential Manager, BUKAN di file
   config, dan TIDAK dikirim ke Muse.
3. Script otomatis:
   login -> cek duplikat -> isi Hadir 08:30-18:00 + kegiatan
   -> Simpan SEKALI -> cek baris hari ini muncul.
4. Hasil dicatat di logbook_run.log.


JADWAL OTOMATIS
---------------
Task "Logbook Dermaga JTI" dibuat otomatis saat jalan pertama
(Senin-Jumat 18:00). Kalau sudah ada, langkah ini dilewati.

Task hanya jalan kalau laptop NYALA dan kamu sedang LOGIN jam 18:00
(popup harus bisa muncul). Kalau laptop mati/terkunci, hari itu
tidak tersimpan, jadi pengingat 20:00 dari Muse tetap penting.

Cara manual (kalau pembuatan otomatis gagal):
  Task Scheduler > Create Basic Task > Weekly, Senin-Jumat, 18:00
  > Start a Program > C:\logbook-dermaga\run_logbook.bat


ATURAN PENTING
--------------
- Popup Cancel / kosong = TIDAK ADA yang disimpan (sengaja).
- Halaman bilang "Logbook hari ini sudah diisi" = script berhenti,
  tidak menyimpan lagi (anti-duplikat).
- Jangan jalankan script lagi atau klik Simpan manual di browser
  setelah script berhasil hari itu.
- JANGAN kirim logbook_config.json, logbook_run.log, atau screenshot
  berisi password/token ke siapa pun, termasuk Muse. Untuk minta
  bantuan, cukup kirim baris log BERHASIL / GAGAL dan nama field
  yang gagal.


KALAU SELECTOR GAGAL
--------------------
Script menebak field form Dermaga (select Keterangan, input Jam
Masuk/Pulang, textarea Pekerjaan). Kalau satu field tidak ketemu,
script BERHENTI SEBELUM Simpan dan menulis nama field di log.
Tidak ada data setengah jadi.

Yang perlu dilakukan:
1. Lihat logbook_run.log, catat field yang gagal.
2. (Opsional) Buka form Dermaga, klik kanan field itu > Inspect,
   catat atribut name/id-nya.
3. Kirim info itu ke Muse untuk perbaikan selector.
Jangan paksa klik Simpan manual berulang kali.
