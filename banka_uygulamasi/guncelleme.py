import requests
import json
import os
import sys
import subprocess
from tkinter import messagebox

SURUM = "1.0.0"
GUNCELLEME_URL = "https://api.github.com/repos/KULLANICI_ADI/banka_uygulamasi/releases/latest"

def surum_kontrol():
    try:
        # GitHub'dan en son sürüm bilgisini al
        yanit = requests.get(GUNCELLEME_URL)
        if yanit.status_code == 200:
            veriler = yanit.json()
            yeni_surum = veriler['tag_name']
            
            if yeni_surum > SURUM:
                if messagebox.askyesno("Güncelleme Mevcut", 
                    f"Yeni sürüm mevcut: {yeni_surum}\nŞu anki sürüm: {SURUM}\n\nGüncellemek ister misiniz?"):
                    guncelleme_indir(veriler['assets'][0]['browser_download_url'])
                    return True
    except Exception as e:
        print(f"Güncelleme kontrolü sırasında hata: {e}")
    return False

def guncelleme_indir(url):
    try:
        # Yeni sürümü indir
        yanit = requests.get(url)
        if yanit.status_code == 200:
            # Geçici dosyaya kaydet
            with open("yeni_surum.exe", "wb") as f:
                f.write(yanit.content)
            
            # Güncelleme betiği oluştur
            with open("guncelle.bat", "w") as f:
                f.write(f'''@echo off
timeout /t 2 /nobreak
del "{sys.executable}"
move /y "yeni_surum.exe" "{sys.executable}"
start "" "{sys.executable}"
del "%~f0"
''')
            
            # Güncelleme betiğini çalıştır
            subprocess.Popen(["guncelle.bat"], shell=True)
            sys.exit()
    except Exception as e:
        messagebox.showerror("Hata", f"Güncelleme sırasında hata oluştu: {e}")
