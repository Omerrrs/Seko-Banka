import requests
import json
import os
from kivy.app import App
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
import subprocess

SURUM = "1.0.0"
GUNCELLEME_URL = "https://github.com/KULLANICI_ADI/sekobanka/releases/latest/download/app-release.apk"

def surum_kontrol():
    try:
        # GitHub'dan en son sürüm bilgisini al
        yanit = requests.get(GUNCELLEME_URL.replace("download/app-release.apk", ""))
        if yanit.status_code == 200:
            veriler = yanit.json()
            yeni_surum = veriler['tag_name']
            
            if yeni_surum > SURUM:
                guncelleme_sor(yeni_surum)
    except Exception as e:
        print(f"Güncelleme kontrolü sırasında hata: {e}")

def guncelleme_sor(yeni_surum):
    content = BoxLayout(orientation='vertical', padding=10)
    content.add_widget(Label(text=f'Yeni sürüm mevcut: {yeni_surum}\nŞu anki sürüm: {SURUM}'))
    
    buttons = BoxLayout(size_hint_y=None, height=40)
    
    # İndir butonu
    indir_btn = Button(text='İndir')
    indir_btn.bind(on_press=lambda x: guncelleme_indir())
    buttons.add_widget(indir_btn)
    
    # İptal butonu
    iptal_btn = Button(text='İptal')
    iptal_btn.bind(on_press=lambda x: popup.dismiss())
    buttons.add_widget(iptal_btn)
    
    content.add_widget(buttons)
    
    popup = Popup(
        title='Güncelleme Mevcut',
        content=content,
        size_hint=(None, None),
        size=(300, 200),
        auto_dismiss=False
    )
    popup.open()

def guncelleme_indir():
    try:
        # APK'yı indir
        yanit = requests.get(GUNCELLEME_URL)
        if yanit.status_code == 200:
            # Downloads klasörüne kaydet
            downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
            apk_path = os.path.join(downloads_path, 'banka_uygulamasi.apk')
            
            with open(apk_path, 'wb') as f:
                f.write(yanit.content)
            
            # APK'yı yükle
            subprocess.Popen(['am', 'start', '-a', 'android.intent.action.VIEW', '-d', 
                            f'file://{apk_path}', 
                            '-t', 'application/vnd.android.package-archive'])
    except Exception as e:
        print(f"Güncelleme indirme sırasında hata: {e}")
