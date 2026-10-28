#!/usr/bin/env python3
"""
Logbook Dermaga JTI - auto-isi dari laptop Windows kamu sendiri.

Cara kerja (sengaja dibuat aman, bukan "tembak buta"):
0. Di awal, script cek dulu apakah Playwright dan Chromium sudah
   terpasang. Kalau belum, muncul pertanyaan:
   "playwright dan chromium belum diinstall, mau install sekarang?"
   - Jawab ya -> script install otomatis, lalu lanjut.
   - Jawab tidak -> script BERHENTI, tidak ada yang disimpan.
0a. Di awal juga, script cek keyring: kalau belum ada, ditawarkan
   install otomatis supaya tombol Simpan Password bisa dipakai.
   Menolak install keyring tidak menghentikan jalan kali ini,
   hanya saja password akan ditanya lagi besok.
0b. Di awal juga, script cek Task Scheduler Windows: kalau task
   "Logbook Dermaga JTI" belum ada, script menawarkan untuk
   membuatnya otomatis (Senin-Jumat 18:00, popup kegiatan).
   Kamu tidak perlu lagi membuka Task Scheduler manual.
   Kalau task sudah ada, langkah ini dilewati begitu saja.
1. Muncul popup: "Kegiatan hari ini apa?"
   - Kalau kamu tekan Cancel / kosong -> TIDAK ADA yang disimpan, script berhenti.
   - Script TIDAK PERNAH mengarang kegiatan.
2. Login ke Dermaga dengan username dari logbook_config.json
   dan password yang kamu isi lewat jendela popup (bukan terminal).
   Jendela password itu punya tombol Simpan Password (checkbox):
   - Dicentang -> password disimpan di Windows Credential Manager
     (lewat keyring), besok tidak ditanya lagi.
   - Tidak dicentang -> password hanya dipakai untuk jalan kali ini.
   Password TIDAK PERNAH dicetak di log dan TIDAK PERNAH dikirim
   ke Muse / ke siapa pun.
3. Buka Monitoring, cek dulu apakah logbook hari ini sudah terisi.
   - Kalau sudah -> berhenti, TIDAK MENYIMPAN LAGI (anti-duplikat).
4. Klik Tambah Logbook, isi: Hadir, 08:30, 18:00, pekerjaan = jawabanmu.
   Tanggal tidak diubah (form Dermaga memang mengunci tanggal hari ini).
5. Klik Simpan SEKALI SAJA, lalu muat ulang Monitoring dan cek
   baris hari ini muncul dengan pekerjaan yang sama.

Lokasi:
- Browser otomatis ini diberi izin geolocation dan dipaksa ke
  lokasi kantor di Denpasar (Jl Tukad Yeh Aya, Renon):
  latitude -8.67714, longitude 115.23964.
  Ini lokasi kerja yang benar, bukan lokasi palsu.
  Di laptop kamu yang memang di Denpasar, lokasi ini juga cocok
  dengan lokasi kerjamu.

Kebutuhan: Python 3.11+ saja. Playwright + Chromium akan ditawarkan
untuk diinstall otomatis di awal kalau belum ada. Kalau mau install
manual juga bisa:
    pip install playwright keyring
    playwright install chromium

Jalankan manual untuk tes pertama:
    python logbook_dermaga.py

Jadwal Senin-Jumat 18:00 dibuat otomatis oleh script di awal
(lihat langkah 0b), jadi tidak perlu lagi membuat task manual
di Task Scheduler. Untuk tes pertama, jalankan manual sekali dan
jawab ya saat ditawari membuat task, lalu cek tasknya muncul di
Task Scheduler. Lihat README_INSTALL.txt.
"""

import getpass
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "logbook_config.json"
LOG_PATH = BASE_DIR / "logbook_run.log"

LOGIN_URL = "https://jti.polinema.ac.id/dermaga/login"
MONITORING_URL = "https://jti.polinema.ac.id/dermaga/mahasiswa/monitoring"

# Lokasi kantor Denpasar (Renon) - lokasi kerja yang benar.
OFFICE_LAT = -8.67714
OFFICE_LNG = 115.23964

JAM_MASUK = "08:30"
JAM_PULANG = "18:00"


def log(msg: str) -> None:
    line = f"{date.today().isoformat()} {msg}"
    print(line, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def ask_yes_no(question: str) -> bool:
    """Tanya ya/tidak. Coba popup dulu, kalau gagal pakai terminal.

    Return True untuk ya, False untuk tidak / dibatalkan / tidak bisa ditanya.
    """
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        answer = messagebox.askyesno("Logbook Dermaga", question)
        root.destroy()
        return bool(answer)
    except Exception:
        pass
    try:
        ans = input(f"{question} (y/n): ").strip().lower()
        return ans in ("y", "ya", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def _chromium_launchable() -> bool:
    """Tes cepat: bisakah Playwright membuka Chromium headless?"""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:
        return False


def ensure_playwright() -> bool:
    """Cek Playwright + Chromium di awal, tawarkan install otomatis.

    Return True kalau sudah siap, False kalau pengguna menolak install
    atau install gagal (script harus berhenti, tidak ada entry dibuat).
    """
    try:
        import playwright  # noqa: F401
        playwright_ok = True
    except ImportError:
        playwright_ok = False

    chromium_ok = _chromium_launchable() if playwright_ok else False

    if playwright_ok and chromium_ok:
        return True

    if not playwright_ok and not chromium_ok:
        question = "playwright dan chromium belum diinstall, mau install sekarang?"
        need_pip = True
        need_browser = True
    elif not playwright_ok:
        question = "playwright belum diinstall, mau install sekarang?"
        need_pip = True
        need_browser = True
    else:
        question = "chromium belum diinstall, mau install sekarang?"
        need_pip = False
        need_browser = True

    print(question)
    log(f"CEK AWAL: {question}")
    if not ask_yes_no(question):
        log("DITOLAK oleh pengguna: install dibatalkan, tidak ada entry yang dibuat.")
        print("Berhenti, tidak ada yang diinstall dan tidak ada entry yang dibuat.")
        return False

    if need_pip:
        print("Menginstall playwright... (ini bisa memakan waktu sebentar)")
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "playwright"],
            check=False,
        )
        if r.returncode != 0:
            log("GAGAL: pip install playwright gagal. Berhenti tanpa menyimpan.")
            return False
    if need_browser:
        print("Menginstall chromium untuk playwright... (download bisa agak besar)")
        r = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=False,
        )
        if r.returncode != 0:
            log("GAGAL: playwright install chromium gagal. Berhenti tanpa menyimpan.")
            return False

    if not _chromium_launchable():
        log("GAGAL: setelah install, Chromium tetap tidak bisa dibuka. Berhenti tanpa menyimpan.")
        return False
    log("CEK AWAL: playwright dan chromium sudah siap.")
    return True


def ensure_keyring() -> None:
    """Cek keyring di awal, tawarkan install otomatis kalau belum ada.

    Ini BUKAN penghenti: kalau pengguna menolak / install gagal,
    jalan kali ini tetap lanjut, hanya saja password tidak bisa
    disimpan dan akan ditanya lagi besok. Return None selalu.
    """
    try:
        import keyring  # noqa: F401

        return
    except ImportError:
        pass
    question = "keyring belum diinstall, mau install sekarang? (supaya tombol Simpan Password bisa dipakai)"
    print(question)
    log(f"CEK AWAL: {question}")
    if not ask_yes_no(question):
        log("keyring: pengguna menolak install, lanjut tanpa menyimpan password.")
        return
    print("Menginstall keyring...")
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", "keyring"],
        check=False,
    )
    if r.returncode == 0:
        log("keyring: berhasil diinstall.")
    else:
        log("keyring: GAGAL diinstall, lanjut tanpa menyimpan password.")


TASK_NAME = "Logbook Dermaga JTI"


def ensure_task_scheduler() -> None:
    """Buat task Task Scheduler otomatis di awal, kalau belum ada.

    Hanya jalan di Windows. Kalau task sudah ada, dilewati.
    Kalau pembuatan gagal, JANGAN menghentikan jalan kali ini:
    logbook hari ini tetap lebih penting, dan user bisa buat
    manual lewat README. Return None dalam semua kasus.
    """
    if sys.platform != "win32":
        return
    script_path = Path(__file__).resolve()
    # 1. Cek apakah task sudah ada.
    check = subprocess.run(
        ["schtasks", "/query", "/tn", TASK_NAME],
        capture_output=True, text=True, check=False,
    )
    if check.returncode == 0:
        log("Task Scheduler: task sudah ada, dilewati.")
        return
    # 2. Tawarkan pembuatan otomatis (bukan diam-diam).
    question = (
        "Task Scheduler untuk logbook belum ada.\n"
        "Buat otomatis sekarang? (Senin-Jumat 18:00, popup kegiatan)"
    )
    if not ask_yes_no(question):
        log("Task Scheduler: pengguna menolak pembuatan otomatis, lanjut jalan kali ini saja.")
        return
    # pythonw.exe di folder yang sama dengan python.exe, supaya tidak
    # muncul jendela terminal saat task jalan nanti.
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    if not pythonw.exists():
        pythonw = exe
    command = f'"{pythonw}" "{script_path}"'
    create = subprocess.run(
        [
            "schtasks", "/create", "/f",
            "/tn", TASK_NAME,
            "/tr", command,
            "/sc", "weekly",
            "/d", "MON,TUE,WED,THU,FRI",
            "/st", "18:00",
        ],
        capture_output=True, text=True, check=False,
    )
    if create.returncode == 0:
        log(f"Task Scheduler: task '{TASK_NAME}' berhasil dibuat (Senin-Jumat 18:00).")
        print(f"Task Scheduler berhasil dibuat: {TASK_NAME} (Senin-Jumat 18:00).")
    else:
        err = (create.stderr or create.stdout or "").strip()
        log(f"Task Scheduler: GAGAL membuat task otomatis ({err}). "
            "Jalan kali ini tetap lanjut; buat manual lewat README kalau perlu.")
        print("Gagal membuat Task Scheduler otomatis, tapi jalan kali ini tetap lanjut.")
        print(f"Detail: {err}")


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        template = {
            "username": "ISI_USERNAME_DERMAGA_KAMU",
            "catatan": "Isi username saja. Password JANGAN ditulis di file ini; "
            "script akan menanyakannya dengan aman, atau menyimpannya "
            "di Windows Credential Manager lewat keyring.",
        }
        CONFIG_PATH.write_text(
            json.dumps(template, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"File config dibuat: {CONFIG_PATH}")
        print("Isi username di file itu, lalu jalankan script lagi.")
        sys.exit(2)
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if not cfg.get("username") or cfg["username"].startswith("ISI_"):
        print("Username di logbook_config.json belum diisi. Isi dulu, lalu jalankan lagi.")
        sys.exit(2)
    return cfg


def ask_kegiatan() -> str | None:
    """Popup kegiatan. Return None kalau dibatalkan / kosong."""
    try:
        import tkinter as tk
        from tkinter import simpledialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        today = date.today().strftime("%d %B %Y")
        kegiatan = simpledialog.askstring(
            "Logbook Dermaga Hari Ini",
            f"Logbook {today}\n\nKegiatan hari ini apa?\n"
            "(Tulis persis seperti yang mau disimpan.\n"
            "Cancel = tidak ada yang disimpan.)",
        )
        root.destroy()
    except Exception:
        kegiatan = input("Kegiatan hari ini (kosong = batal): ").strip() or None
    if kegiatan is None:
        return None
    kegiatan = kegiatan.strip()
    return kegiatan or None


def _ask_password_gui(username: str):
    """Jendela password dengan tombol Simpan Password (checkbox).

    Return (password, simpan) atau (None, False) kalau dibatalkan.
    Kalau tkinter gagal, return (None, None) sebagai tanda pakai fallback terminal.
    """
    try:
        import tkinter as tk
        from tkinter import ttk

        try:
            import keyring as _kr
            keyring_ok = True
        except Exception:
            _kr = None
            keyring_ok = False

        result: dict = {"pw": None, "simpan": False, "ok": False}

        root = tk.Tk()
        root.title("Logbook Dermaga - Password")
        root.attributes("-topmost", True)
        root.resizable(False, False)

        ttk.Label(root, text=f"Password Dermaga untuk {username}").pack(padx=20, pady=(15, 5), anchor="w")
        entry = ttk.Entry(root, show="*", width=40)
        entry.pack(padx=20, pady=5)
        entry.focus_set()

        simpan_var = tk.BooleanVar(value=False)
        # Checkbox SELALU aktif, jangan dinonaktifkan kalau keyring belum
        # ada: kalau dicentang, script akan install keyring dulu lalu
        # menyimpan. Menonaktifkannya adalah bug versi sebelumnya yang
        # membuat user mentok tanpa bisa menyimpan apa-apa.
        ttk.Checkbutton(
            root,
            text="Simpan password (Windows Credential Manager)",
            variable=simpan_var,
        ).pack(padx=20, pady=5, anchor="w")
        if not keyring_ok:
            ttk.Label(
                root,
                text="Catatan: keyring belum terpasang. Kalau checkbox di atas\n"
                "dicentang, script akan menginstall keyring dulu, lalu menyimpan.",
            ).pack(padx=20, pady=5, anchor="w")

        def on_ok(_event=None):
            result["pw"] = entry.get().strip()
            result["simpan"] = bool(simpan_var.get())
            result["ok"] = True
            root.destroy()

        def on_cancel(_event=None):
            result["ok"] = False
            root.destroy()

        btn_frame = ttk.Frame(root)
        btn_frame.pack(padx=20, pady=(5, 15))
        ttk.Button(btn_frame, text="Simpan Password & Lanjut", command=on_ok).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Batal", command=on_cancel).pack(side="left", padx=5)
        root.bind("<Return>", on_ok)
        root.bind("<Escape>", on_cancel)
        root.mainloop()

        if not result["ok"] or not result["pw"]:
            return None, False
        return result["pw"], result["simpan"]
    except Exception:
        return None, None


def get_password(username: str) -> str:
    """Ambil password: Credential Manager dulu, kalau belum ada pakai popup.

    Popup password punya checkbox 'Simpan password' sebagai tombol
    simpannya (bukan pertanyaan terminal). Kalau checkbox dicentang
    dan keyring tersedia, password disimpan di Windows Credential
    Manager, bukan di file config.
    """
    try:
        import keyring

        saved = keyring.get_password("dermaga-jti-logbook", username)
        if saved:
            return saved
    except Exception:
        keyring = None  # type: ignore

    pw, simpan = _ask_password_gui(username)
    if pw is None and simpan is None:
        # Fallback terminal (misal tkinter tidak tersedia).
        pw = getpass.getpass("Password Dermaga (tidak akan terlihat saat diketik): ").strip()
        if not pw:
            print("Password kosong, berhenti tanpa menyimpan.")
            sys.exit(2)
        if keyring is not None:
            try:
                ans = input("Simpan password di Windows Credential Manager? (y/N): ").strip().lower()
                if ans == "y":
                    keyring.set_password("dermaga-jti-logbook", username, pw)
            except Exception:
                pass
        return pw
    if not pw:
        print("Password dibatalkan, berhenti tanpa menyimpan.")
        sys.exit(2)

    if simpan:
        if keyring is not None:
            try:
                keyring.set_password("dermaga-jti-logbook", username, pw)
                print("Password disimpan di Credential Manager (bukan di file ini).")
            except Exception as exc:
                print(f"Gagal menyimpan ke Credential Manager, lanjut tanpa menyimpan: {exc}")
        else:
            # Coba install keyring sekali, supaya checkbox tadi benar-benar
            # berfungsi di jalan berikutnya, tapi jangan gagalkan jalan ini.
            try:
                r = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "keyring"],
                    capture_output=True, text=True, check=False,
                )
                if r.returncode == 0:
                    import keyring as kr2

                    kr2.set_password("dermaga-jti-logbook", username, pw)
                    print("Password disimpan di Credential Manager (bukan di file ini).")
                else:
                    print("keyring belum terpasang, password tidak disimpan. Akan ditanya lagi besok.")
            except Exception:
                print("keyring belum terpasang, password tidak disimpan. Akan ditanya lagi besok.")
    return pw


def fill_first(locator, values, field_name: str) -> bool:
    """Coba isi field dengan beberapa selector kandidat, satu per satu."""
    for value in values:
        try:
            loc = locator(value)
            if loc.count() >= 1:
                first = loc.first
                first.wait_for(state="visible", timeout=5000)
                if first.evaluate("el => el.tagName") == "SELECT":
                    first.select_option(label=field_name)
                else:
                    first.fill(field_name)
                return True
        except Exception:
            continue
    return False


def main() -> int:
    # 0. Cek Playwright + Chromium di awal, sebelum tanya kegiatan.
    if not ensure_playwright():
        return 2

    # 0a. Cek keyring di awal, supaya tombol Simpan Password bisa dipakai.
    #     Menolak / gagal install tidak menghentikan jalan kali ini.
    ensure_keyring()

    # 0b. Buat Task Scheduler otomatis di awal, kalau belum ada.
    #     Gagal membuat task tidak menghentikan jalan kali ini.
    ensure_task_scheduler()

    cfg = load_config()
    username = cfg["username"]

    kegiatan = ask_kegiatan()
    if not kegiatan:
        log("DIBATALKAN oleh pengguna: tidak ada entry yang dibuat.")
        return 0

    password = get_password(username)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright belum terpasang. Jalankan: pip install playwright && playwright install chromium")
        return 2

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            permissions=["geolocation"],
            geolocation={"latitude": OFFICE_LAT, "longitude": OFFICE_LNG},
            locale="id-ID",
            timezone_id="Asia/Makassar",
        )
        page = context.new_page()

        # 1. Login
        log("Login ke Dermaga...")
        page.goto(LOGIN_URL, wait_until="networkidle", timeout=60000)
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)
        page.click("#btnLogin")
        page.wait_for_url("**/dermaga/**", timeout=60000)
        if "login" in page.url:
            log("GAGAL: masih di halaman login. Cek username/password, lalu coba lagi. Tidak ada entry dibuat.")
            return 3
        log("Login berhasil.")

        # 2. Monitoring + cek duplikat
        page.goto(MONITORING_URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2000)
        body = page.locator("body").inner_text()
        if "sudah diisi" in body.lower() or "logbook hari ini sudah diisi" in body.lower():
            log("SUDAH TERISI hari ini menurut halaman. Tidak menyimpan lagi (anti-duplikat).")
            return 0

        # 3. Buka form Tambah Logbook
        log("Membuka form Tambah Logbook...")
        try:
            page.get_by_role("button", name="Tambah Logbook").first.click(timeout=10000)
        except Exception:
            page.locator("text=Tambah Logbook").first.click(timeout=10000)
        page.wait_for_timeout(1500)

        # 4. Isi form. Kalau ada satu field yang tidak ketemu, BERHENTI
        #    SEBELUM Simpan, supaya tidak ada entry setengah-setengah.
        ok_hadir = False
        for sel in ["select", 'select[name*="keterangan"]', 'select[name*="status"]']:
            try:
                loc = page.locator(sel).first
                if loc.count() >= 1:
                    loc.select_option(label="Hadir")
                    ok_hadir = True
                    break
            except Exception:
                continue
        if not ok_hadir:
            # Keterangan bisa jadi radio button, bukan select.
            try:
                page.get_by_label("Hadir").first.check(timeout=5000)
                ok_hadir = True
            except Exception:
                pass
        if not ok_hadir:
            log("GAGAL: field Keterangan/Hadir tidak ketemu. Berhenti SEBELUM Simpan.")
            log("Lihat README bagian 'Kalau selector gagal' dan kirim nama field-nya ke Muse.")
            return 4

        def fill_time(field_candidates, value, label):
            for cand in field_candidates:
                try:
                    loc = page.locator(cand).first
                    if loc.count() >= 1:
                        loc.fill(value)
                        return True
                except Exception:
                    continue
            log(f"GAGAL: field {label} tidak ketemu. Berhenti SEBELUM Simpan.")
            return False

        if not fill_time(
            ['input[name*="masuk"]', 'input[name*="jam_masuk"]', 'input[placeholder*="Masuk"]'],
            JAM_MASUK, "Jam Masuk",
        ):
            return 4
        if not fill_time(
            ['input[name*="pulang"]', 'input[name*="jam_pulang"]', 'input[placeholder*="Pulang"]'],
            JAM_PULANG, "Jam Pulang",
        ):
            return 4

        pekerjaan_ok = False
        for cand in [
            'textarea[name*="pekerjaan"]',
            'textarea[name*="kegiatan"]',
            'textarea[name*="keterangan"]',
            "textarea",
            'input[name*="pekerjaan"]',
        ]:
            try:
                loc = page.locator(cand).first
                if loc.count() >= 1:
                    loc.fill(kegiatan)
                    pekerjaan_ok = True
                    break
            except Exception:
                continue
        if not pekerjaan_ok:
            log("GAGAL: field Pekerjaan tidak ketemu. Berhenti SEBELUM Simpan.")
            return 4

        # 5. Simpan SEKALI SAJA
        log("Menyimpan SEKALI...")
        try:
            page.get_by_role("button", name="Simpan").first.click(timeout=10000)
        except Exception:
            page.locator("text=Simpan").first.click(timeout=10000)
        page.wait_for_timeout(3000)

        # 6. Verifikasi: muat ulang Monitoring, cek baris hari ini
        page.goto(MONITORING_URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2000)
        body2 = page.locator("body").inner_text()
        if kegiatan[:40] in body2 and "sudah diisi" in body2.lower():
            log("BERHASIL: baris logbook hari ini sudah muncul di daftar.")
            browser.close()
            return 0
        if kegiatan[:40] in body2:
            log("KEMUNGKINAN BERHASIL: teks kegiatan ditemukan di daftar, cek manual statusnya.")
            browser.close()
            return 0
        log("PERLU CEK MANUAL: setelah Simpan, teks kegiatan belum terlihat di daftar. "
            "Buka Monitoring dan cek baris hari ini sebelum mengulang (jangan klik Simpan dua kali).")
        browser.close()
        return 5


if __name__ == "__main__":
    sys.exit(main())
