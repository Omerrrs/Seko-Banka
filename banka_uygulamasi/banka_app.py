import tkinter as tk
from tkinter import messagebox, simpledialog
import hashlib
from veritabani import Veritabani
import requests
import json
import os
import uuid
import winreg
from guncelleme import surum_kontrol, SURUM

# Pushbullet API anahtarınızı buraya ekleyin
PUSHBULLET_API_KEY = 'o.5adp1v9WlPQ4IcMvYolBQXoDLzjMNAnm'

# Pushbullet objesi oluşturma
try:
    from pushbullet import Pushbullet
    pb = Pushbullet(PUSHBULLET_API_KEY)
except ImportError:
    print("Pushbullet modülü yüklü değil. Lütfen 'pip install pushbullet.py' komutunu kullanarak yükleyin.")
    pb = None
except Exception as e:
    print(f"Pushbullet bağlantı hatası: {e}")
    pb = None

# Banka Hesabı Sınıfı
class BankaHesabi:
    def __init__(self, id, hesap_sahibi, bakiye=0, donduruldu=0, yas=0, cinsiyet=""):
        self.id = id
        self.hesap_sahibi = hesap_sahibi
        self.bakiye = bakiye
        self.donduruldu = donduruldu == 1
        self.yas = yas
        self.cinsiyet = cinsiyet
        self.db = Veritabani()

    def hesap_dondur_kontrol(self):
        return self.donduruldu

    def para_yatir(self, miktar):
        if self.hesap_dondur_kontrol():
            self.bildirim_gonder("Hesap donduruldu. İşlem yapılamıyor.")
            return False
        if miktar > 0:
            self.bakiye += miktar
            self.db.bakiye_guncelle(self.id, self.bakiye)
            self.db.islem_ekle(self.id, "para_yatirma", miktar, f"{miktar} TL yatırıldı.")
            self.bildirim_gonder(f"{miktar} TL yatırıldı.")
            return True
        return False

    def para_cek(self, miktar):
        if self.hesap_dondur_kontrol():
            self.bildirim_gonder("Hesap donduruldu. İşlem yapılamıyor.")
            return False
        if 0 < miktar <= self.bakiye:
            self.bakiye -= miktar
            self.db.bakiye_guncelle(self.id, self.bakiye)
            self.db.islem_ekle(self.id, "para_cekme", -miktar, f"{miktar} TL çekildi.")
            self.bildirim_gonder(f"{miktar} TL çekildi.")
            return True
        return False

    def urun_satinal(self, urun, fiyat):
        if self.hesap_dondur_kontrol():
            self.bildirim_gonder("Hesap donduruldu. İşlem yapılamıyor.")
            return False
        if fiyat > 0 and fiyat <= self.bakiye:
            self.bakiye -= fiyat
            self.db.bakiye_guncelle(self.id, self.bakiye)
            self.db.islem_ekle(self.id, "alisveris", -fiyat, f"{urun} satın alındı. {fiyat} TL harcandı.")
            self.bildirim_gonder(f"{urun} satın alındı. {fiyat} TL harcandı.")
            return True
        return False

    def hesap_ozeti(self):
        ozet = f"--- {self.hesap_sahibi} Hesap Özeti ---\n"
        islemler = self.db.islem_gecmisi_getir(self.id)
        for islem in islemler:
            _, miktar, aciklama, tarih = islem
            ozet += f"{tarih}: {aciklama}\n"
        ozet += f"\nGüncel Bakiye: {self.bakiye} TL\nYaş: {self.yas}\nCinsiyet: {self.cinsiyet}"
        return ozet

    def bildirim_gonder(self, mesaj):
        if pb:
            try:
                pb.push_note("Banka Bildirimi", mesaj)
            except Exception as e:
                print(f"Bildirim gönderilemedi: {e}")

    def sifre_degistir(self, yeni_sifre):
        if yeni_sifre:
            self.db.sifre_guncelle(self.id, yeni_sifre)
            self.db.islem_ekle(self.id, "sifre_degisiklik", 0, "Şifre değiştirildi.")
            self.bildirim_gonder("Şifre değiştirildi.")
            return True
        return False

# Banka Sınıfı
class Banka:
    def __init__(self):
        self.db = Veritabani()

    def hesap_olustur(self, hesap_sahibi, sifre):
        if self.db.hesap_var_mi(hesap_sahibi):
            return False
        sonuc = self.db.hesap_olustur(hesap_sahibi, sifre)
        if sonuc:
            hesap = self.hesap_getir(hesap_sahibi, sifre)
            # Yeni hesap için otomatik banka kartı oluştur
            self.db.kart_olustur(hesap['id'], "Banka Kartı")
        return sonuc

    def kart_olustur(self, hesap_id, kart_turu, limit=0):
        return self.db.kart_olustur(hesap_id, kart_turu, limit)

    def kartlari_getir(self, hesap_id):
        return self.db.kartlari_getir(hesap_id)

    def kart_sil(self, kart_numarasi, hesap_id):
        return self.db.kart_sil(kart_numarasi, hesap_id)

    def kart_guncelle(self, kart_numarasi, hesap_id, yeni_limit=None, aktif=None):
        return self.db.kart_guncelle(kart_numarasi, hesap_id, yeni_limit, aktif)

    def hesap_getir(self, hesap_sahibi, sifre):
        hesap_verisi = self.db.hesap_getir(hesap_sahibi, sifre)
        if hesap_verisi:
            id, hesap_sahibi, _, bakiye, donduruldu, yas, cinsiyet, _ = hesap_verisi
            return BankaHesabi(id, hesap_sahibi, bakiye, donduruldu, yas, cinsiyet)
        return None

# Ürün Listesi
urunler = {
    # Kırtasiye
    "Kitap": 120,
    "Kalem": 25,
    "Defter": 45,
    "Çanta": 350,
    
    # Elektronik
    "Laptop": 25000,
    "Telefon": 15000,
    "Tablet": 8000,
    "Kulaklık": 1200,
    "Akıllı Saat": 3500,
    "Powerbank": 800,
    
    # Giyim
    "Kıyafet": 750,
    "Ayakkabı": 1500,
    "Gözlük": 850,
    "Mont": 2500,
    "Pantolon": 600,
    "Gömlek": 450,
    
    # Market
    "Elma (kg)": 25,
    "Muz (kg)": 45,
    "Portakal (kg)": 30,
    "Domates (kg)": 35,
    "Salatalık (kg)": 40,
    "Patates (kg)": 30,
    "Havuç (kg)": 35,
    
    # İçecekler
    "Ayran": 15,
    "Su (1L)": 8,
    "Kola": 25,
    "Çay (kg)": 180,
    "Kahve (250g)": 150,
    
    # Hazır Yemek
    "Hamburger": 120,
    "Pizza": 160,
    "Sandviç": 80,
    "Döner": 90,
    
    # Araçlar
    "Toyota Corolla": 950000,
    "BMW 3 Serisi": 2500000,
    "Mercedes C Serisi": 3000000,
    "Yamaha MT-07": 450000,
    "Honda CBR500R": 500000,
    
    # Teknoloji
    "DJI Mini 3 Drone": 25000,
    "DJI Mavic 3": 75000,
    "PlayStation 5": 18000,
    "Xbox Series X": 17000,
    "Gaming Laptop": 45000,
    
    # Mücevherat
    "Altın Bilezik (22 Ayar)": 25000,
    "Altın Yüzük (14 Ayar)": 8000,
    "Pırlanta Yüzük": 35000,
    "Altın Kolye (22 Ayar)": 15000,
    "Pırlanta Kolye": 45000,
    
    # Ev Eşyaları
    "Buzdolabı": 35000,
    "Çamaşır Makinesi": 25000,
    "Televizyon (55 inç)": 22000,
    "Mikrodalga Fırın": 4500,
    "Robot Süpürge": 12000
}

# GUI Uygulaması
class BankaUygulamasi:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"Banka Uygulaması v{SURUM}")
        self.root.geometry("800x600")
        self.root.configure(bg='#004B93')  # Yapı Kredi lacivert
        
        # Güncelleme kontrolü
        self.root.after(1000, self.guncelleme_kontrol)
        
        # Stil ayarları
        self.stil = {
            'bg': '#004B93',  # Arka plan - lacivert
            'fg': 'white',    # Yazı rengi - beyaz
            'button_bg': '#0063CC',  # Buton arka plan - açık mavi
            'button_fg': 'white',    # Buton yazı - beyaz
            'entry_bg': 'white',     # Giriş alanı - beyaz
            'entry_fg': '#004B93',   # Giriş alanı yazı - lacivert
            'font': ('Arial', 12),   # Varsayılan font
            'title_font': ('Arial', 24, 'bold'),  # Başlık font
            'button_font': ('Arial', 12, 'bold')  # Buton font
        }
        
        self.banka = Banka()
        self.aktif_hesap = None
        self.cihaz_id = self.cihaz_id_al()
        self.son_kullanici = self.son_kullanici_oku()
        
        if self.son_kullanici:
            self.giris_pencere_olustur(self.son_kullanici)
        else:
            self.ana_menu_olustur()

    def cihaz_id_al(self):
        try:
            # Windows Registry'den cihaz ID'sini almaya çalış
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\BankaUygulamasi", 0, winreg.KEY_READ)
            cihaz_id = winreg.QueryValueEx(key, "CihazID")[0]
            winreg.CloseKey(key)
            return cihaz_id
        except:
            try:
                # Eğer ID yoksa yeni bir ID oluştur ve kaydet
                cihaz_id = str(uuid.uuid4())
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\BankaUygulamasi")
                winreg.SetValueEx(key, "CihazID", 0, winreg.REG_SZ, cihaz_id)
                winreg.CloseKey(key)
                return cihaz_id
            except:
                # Registry'e yazılamazsa dosya sistemini kullan
                if not os.path.exists("cihaz_id.txt"):
                    cihaz_id = str(uuid.uuid4())
                    with open("cihaz_id.txt", "w") as f:
                        f.write(cihaz_id)
                    return cihaz_id
                with open("cihaz_id.txt", "r") as f:
                    return f.read().strip()

    def son_kullanici_oku(self):
        try:
            with open(f"son_giris_{self.cihaz_id}.json", "r") as dosya:
                veri = json.load(dosya)
                return veri.get("son_kullanici", "")
        except:
            return ""

    def son_kullanici_kaydet(self, kullanici_adi):
        with open(f"son_giris_{self.cihaz_id}.json", "w") as dosya:
            json.dump({"son_kullanici": kullanici_adi}, dosya)

    def buton_olustur(self, parent, text, command, width=20):
        return tk.Button(parent, text=text, command=command, width=width,
                        bg=self.stil['button_bg'], fg=self.stil['button_fg'],
                        font=self.stil['button_font'], cursor='hand2',
                        activebackground='#0052A3', activeforeground='white',
                        relief=tk.FLAT, padx=10, pady=5)

    def etiket_olustur(self, parent, text, font=None):
        if font is None:
            font = self.stil['font']
        return tk.Label(parent, text=text, bg=self.stil['bg'], fg=self.stil['fg'],
                       font=font)

    def giris_alani_olustur(self, parent):
        entry = tk.Entry(parent, bg=self.stil['entry_bg'], fg=self.stil['entry_fg'],
                        font=self.stil['font'], relief=tk.FLAT)
        entry.configure(insertbackground=self.stil['entry_fg'])  # İmleç rengi
        return entry

    def ana_menu_olustur(self):
        # Mevcut widget'ları temizle
        for widget in self.root.winfo_children():
            widget.destroy()
            
        # Logo ve başlık çerçevesi
        baslik_frame = tk.Frame(self.root, bg=self.stil['bg'])
        baslik_frame.pack(pady=40)
        
        # Başlık
        baslik = self.etiket_olustur(baslik_frame, "Banka Uygulaması", self.stil['title_font'])
        baslik.pack()
        
        # Alt başlık
        alt_baslik = self.etiket_olustur(baslik_frame, "Hoş Geldiniz", ('Arial', 14))
        alt_baslik.pack(pady=10)
        
        # Butonlar için çerçeve
        buton_frame = tk.Frame(self.root, bg=self.stil['bg'])
        buton_frame.pack(pady=20)
        
        # Giriş/Kayıt butonları
        giris_btn = self.buton_olustur(buton_frame, "Giriş Yap", self.giris_pencere_olustur)
        giris_btn.pack(pady=10)
        
        kayit_btn = self.buton_olustur(buton_frame, "Hesap Oluştur", self.kayit_pencere_olustur)
        kayit_btn.pack(pady=10)
        
        cikis_btn = self.buton_olustur(buton_frame, "Çıkış", self.root.quit)
        cikis_btn.pack(pady=10)

    def sifre_goster_gizle(self, sifre_entry, goster_gizle_btn):
        if sifre_entry['show'] == '*':
            sifre_entry.config(show='')
            goster_gizle_btn.config(text='Şifreyi Gizle')
        else:
            sifre_entry.config(show='*')
            goster_gizle_btn.config(text='Şifreyi Göster')

    def giris_pencere_olustur(self, varsayilan_kullanici=None):
        # Yeni pencere oluştur
        giris_pencere = tk.Toplevel(self.root)
        giris_pencere.title("Giriş Yap")
        giris_pencere.geometry("400x500")
        giris_pencere.configure(bg=self.stil['bg'])
        
        # Başlık
        baslik = self.etiket_olustur(giris_pencere, "Giriş Yap", self.stil['title_font'])
        baslik.pack(pady=30)

        # Form çerçevesi
        form_frame = tk.Frame(giris_pencere, bg=self.stil['bg'])
        form_frame.pack(pady=20)

        # Hesap sahibi
        if varsayilan_kullanici:
            self.etiket_olustur(form_frame, f"Hoş geldin, {varsayilan_kullanici}").pack(pady=5)
            hesap_entry = tk.Entry(form_frame)
            hesap_entry.insert(0, varsayilan_kullanici)
            hesap_entry.pack_forget()  # Gizle
        else:
            self.etiket_olustur(form_frame, "Hesap Sahibi:").pack(pady=5)
            hesap_entry = self.giris_alani_olustur(form_frame)
            hesap_entry.pack(pady=5)

        # Şifre
        self.etiket_olustur(form_frame, "Şifre:").pack(pady=5)
        sifre_frame = tk.Frame(form_frame, bg=self.stil['bg'])
        sifre_frame.pack(pady=5)
        
        sifre_entry = self.giris_alani_olustur(sifre_frame)
        sifre_entry.configure(show="*")
        sifre_entry.pack(side=tk.LEFT, padx=5)
        
        goster_gizle_btn = self.buton_olustur(sifre_frame, "👁", 
                                           lambda: self.sifre_goster_gizle(sifre_entry, goster_gizle_btn),
                                           width=3)
        goster_gizle_btn.pack(side=tk.LEFT)

        def giris_yap():
            hesap_sahibi = hesap_entry.get() if not varsayilan_kullanici else varsayilan_kullanici
            sifre = sifre_entry.get()
            
            if hesap_sahibi and sifre:
                hesap = self.banka.hesap_getir(hesap_sahibi, sifre)
                if hesap:
                    self.aktif_hesap = hesap
                    self.son_kullanici_kaydet(hesap_sahibi)  # Son kullanıcıyı kaydet
                    giris_pencere.destroy()
                    self.hesap_menu_olustur()
                else:
                    messagebox.showerror("Hata", "Geçersiz şifre!")
            else:
                messagebox.showerror("Hata", "Lütfen tüm alanları doldurun!")

        # Giriş butonu
        giris_btn = self.buton_olustur(giris_pencere, "Giriş Yap", giris_yap)
        giris_btn.pack(pady=20)

        # Farklı hesapla giriş yap butonu (sadece varsayılan kullanıcı varsa göster)
        if varsayilan_kullanici:
            def farkli_hesap():
                giris_pencere.destroy()
                self.giris_pencere_olustur(None)
            
            farkli_hesap_btn = self.buton_olustur(giris_pencere, "Farklı Hesapla Giriş Yap", farkli_hesap)
            farkli_hesap_btn.pack(pady=10)

    def kayit_pencere_olustur(self):
        # Yeni pencere oluştur
        kayit_pencere = tk.Toplevel(self.root)
        kayit_pencere.title("Hesap Oluştur")
        kayit_pencere.geometry("400x500")
        kayit_pencere.configure(bg=self.stil['bg'])
        
        # Başlık
        baslik = self.etiket_olustur(kayit_pencere, "Hesap Oluştur", self.stil['title_font'])
        baslik.pack(pady=30)

        # Form çerçevesi
        form_frame = tk.Frame(kayit_pencere, bg=self.stil['bg'])
        form_frame.pack(pady=20)

        # Hesap sahibi
        self.etiket_olustur(form_frame, "Hesap Sahibi:").pack(pady=5)
        hesap_entry = self.giris_alani_olustur(form_frame)
        hesap_entry.pack(pady=5)

        # Şifre
        self.etiket_olustur(form_frame, "Şifre:").pack(pady=5)
        sifre_frame = tk.Frame(form_frame, bg=self.stil['bg'])
        sifre_frame.pack(pady=5)
        
        sifre_entry = self.giris_alani_olustur(sifre_frame)
        sifre_entry.configure(show="*")
        sifre_entry.pack(side=tk.LEFT, padx=5)
        
        goster_gizle_btn = self.buton_olustur(sifre_frame, "👁", 
                                           lambda: self.sifre_goster_gizle(sifre_entry, goster_gizle_btn),
                                           width=3)
        goster_gizle_btn.pack(side=tk.LEFT)

        def kayit_ol():
            hesap_sahibi = hesap_entry.get()
            sifre = sifre_entry.get()
            
            if hesap_sahibi and sifre:
                if self.banka.hesap_olustur(hesap_sahibi, sifre):
                    messagebox.showinfo("Başarılı", "Hesap başarıyla oluşturuldu!")
                    kayit_pencere.destroy()
                else:
                    messagebox.showerror("Hata", "Bu hesap zaten mevcut!")
            else:
                messagebox.showerror("Hata", "Lütfen tüm alanları doldurun!")

        # Kayıt butonu
        kayit_btn = self.buton_olustur(kayit_pencere, "Hesap Oluştur", kayit_ol)
        kayit_btn.pack(pady=30)

    def hesap_menu_olustur(self):
        # Mevcut widget'ları temizle
        for widget in self.root.winfo_children():
            widget.destroy()

        # Başlık
        baslik = self.etiket_olustur(self.root, f"Hoş Geldiniz, {self.aktif_hesap.hesap_sahibi}", self.stil['title_font'])
        baslik.pack(pady=30)

        # Bakiye göster
        bakiye_text = f"Bakiye: {self.aktif_hesap.bakiye:.2f} TL"
        bakiye_label = self.etiket_olustur(self.root, bakiye_text)
        bakiye_label.pack(pady=10)

        # Butonlar için frame
        buton_frame = tk.Frame(self.root, bg=self.stil['bg'])
        buton_frame.pack(pady=20)

        # İşlem butonları
        self.buton_olustur(buton_frame, "Para Yatır", self.para_yatir_pencere).pack(pady=5)
        self.buton_olustur(buton_frame, "Para Çek", self.para_cek_pencere).pack(pady=5)
        self.buton_olustur(buton_frame, "Para Gönder", self.para_gonder_pencere).pack(pady=5)
        self.buton_olustur(buton_frame, "İşlem Geçmişi", self.islem_gecmisi_goster).pack(pady=5)
        self.buton_olustur(buton_frame, "Kartlarım", self.kartlarim_pencere).pack(pady=5)
        self.buton_olustur(buton_frame, "Hesap Özeti", self.hesap_ozeti_goster).pack(pady=5)
        self.buton_olustur(buton_frame, "Çıkış Yap", self.cikis_yap).pack(pady=5)

    def kartlarim_pencere(self):
        # Yeni pencere
        kart_pencere = tk.Toplevel(self.root)
        kart_pencere.title("Kartlarım")
        kart_pencere.geometry("600x800")
        kart_pencere.configure(bg=self.stil['bg'])

        # Başlık
        baslik = self.etiket_olustur(kart_pencere, "Kartlarım", self.stil['title_font'])
        baslik.pack(pady=20)

        # Mevcut kartları listele
        kartlar = self.banka.kartlari_getir(self.aktif_hesap.id)
        
        if kartlar:
            for kart in kartlar:
                kart_frame = tk.Frame(kart_pencere, bg=self.stil['bg'], relief=tk.RAISED, borderwidth=1)
                kart_frame.pack(pady=10, padx=20, fill=tk.X)
                
                # Kart bilgileri
                kart_turu = kart[0]
                kart_no = f"**** **** **** {kart[1][-4:]}"
                son_kullanim = kart[2]
                limit = kart[3]
                aktif = kart[4]
                
                # Kart detayları
                self.etiket_olustur(kart_frame, f"Kart Türü: {kart_turu}").pack(anchor='w', padx=10)
                self.etiket_olustur(kart_frame, f"Kart No: {kart_no}").pack(anchor='w', padx=10)
                self.etiket_olustur(kart_frame, f"Son Kullanım: {son_kullanim}").pack(anchor='w', padx=10)
                if limit > 0:
                    self.etiket_olustur(kart_frame, f"Limit: {limit:.2f} TL").pack(anchor='w', padx=10)
                
                durum = "Aktif" if aktif else "Pasif"
                durum_label = self.etiket_olustur(kart_frame, f"Durum: {durum}")
                durum_label.pack(anchor='w', padx=10)
                
                # Kart işlemleri için butonlar
                buton_frame = tk.Frame(kart_frame, bg=self.stil['bg'])
                buton_frame.pack(pady=5)
                
                if aktif:
                    self.buton_olustur(buton_frame, "Dondur", 
                                     lambda k=kart[1]: self.kart_dondur(k), width=10).pack(side=tk.LEFT, padx=5)
                else:
                    self.buton_olustur(buton_frame, "Aktifleştir", 
                                     lambda k=kart[1]: self.kart_aktif(k), width=10).pack(side=tk.LEFT, padx=5)
                
                self.buton_olustur(buton_frame, "Sil", 
                                 lambda k=kart[1]: self.kart_sil(k, kart_frame), width=10).pack(side=tk.LEFT, padx=5)
                
                if kart_turu != "Banka Kartı":
                    self.buton_olustur(buton_frame, "Limit Güncelle", 
                                     lambda k=kart[1]: self.limit_guncelle(k), width=15).pack(side=tk.LEFT, padx=5)
        
        # Yeni kart oluştur butonu
        yeni_kart_frame = tk.Frame(kart_pencere, bg=self.stil['bg'])
        yeni_kart_frame.pack(pady=20)
        
        self.buton_olustur(yeni_kart_frame, "Yeni Kart Oluştur", self.yeni_kart_olustur).pack()

    def yeni_kart_olustur(self):
        # Kart türü seçim penceresi
        kart_turu_pencere = tk.Toplevel(self.root)
        kart_turu_pencere.title("Yeni Kart")
        kart_turu_pencere.geometry("400x300")
        kart_turu_pencere.configure(bg=self.stil['bg'])
        
        baslik = self.etiket_olustur(kart_turu_pencere, "Kart Türü Seçin", self.stil['title_font'])
        baslik.pack(pady=20)
        
        def kart_olustur(turu, limit=0):
            if self.banka.kart_olustur(self.aktif_hesap.id, turu, limit):
                messagebox.showinfo("Başarılı", f"Yeni {turu} oluşturuldu!")
                kart_turu_pencere.destroy()
                self.kartlarim_pencere().destroy()
                self.kartlarim_pencere()  # Kartlar sayfasını yenile
            else:
                messagebox.showerror("Hata", "Kart oluşturulamadı!")

        def kredi_karti_olustur():
            try:
                limit = float(simpledialog.askstring("Limit", "Kredi kartı limitini girin (TL):"))
                if limit > 0:
                    kart_olustur("Kredi Kartı", limit)
            except:
                messagebox.showerror("Hata", "Geçersiz limit!")

        self.buton_olustur(kart_turu_pencere, "Banka Kartı", 
                          lambda: kart_olustur("Banka Kartı")).pack(pady=10)
        self.buton_olustur(kart_turu_pencere, "Kredi Kartı", 
                          kredi_karti_olustur).pack(pady=10)
        self.buton_olustur(kart_turu_pencere, "Sanal Kart", 
                          lambda: kart_olustur("Sanal Kart")).pack(pady=10)

    def kart_dondur(self, kart_numarasi):
        if self.banka.kart_guncelle(kart_numarasi, self.aktif_hesap.id, aktif=False):
            messagebox.showinfo("Başarılı", "Kart donduruldu!")
            self.kartlarim_pencere().destroy()
            self.kartlarim_pencere()  # Sayfayı yenile
        else:
            messagebox.showerror("Hata", "Kart dondurulamadı!")

    def kart_aktif(self, kart_numarasi):
        if self.banka.kart_guncelle(kart_numarasi, self.aktif_hesap.id, aktif=True):
            messagebox.showinfo("Başarılı", "Kart aktifleştirildi!")
            self.kartlarim_pencere().destroy()
            self.kartlarim_pencere()  # Sayfayı yenile
        else:
            messagebox.showerror("Hata", "Kart aktifleştirilemedi!")

    def kart_sil(self, kart_numarasi, kart_frame):
        if messagebox.askyesno("Onay", "Bu kartı silmek istediğinize emin misiniz?"):
            if self.banka.kart_sil(kart_numarasi, self.aktif_hesap.id):
                messagebox.showinfo("Başarılı", "Kart silindi!")
                kart_frame.destroy()
            else:
                messagebox.showerror("Hata", "Kart silinemedi!")

    def limit_guncelle(self, kart_numarasi):
        try:
            yeni_limit = float(simpledialog.askstring("Limit", "Yeni limit değerini girin (TL):"))
            if yeni_limit > 0:
                if self.banka.kart_guncelle(kart_numarasi, self.aktif_hesap.id, yeni_limit=yeni_limit):
                    messagebox.showinfo("Başarılı", "Limit güncellendi!")
                    self.kartlarim_pencere().destroy()
                    self.kartlarim_pencere()  # Sayfayı yenile
                else:
                    messagebox.showerror("Hata", "Limit güncellenemedi!")
        except:
            messagebox.showerror("Hata", "Geçersiz limit değeri!")

    def para_yatir_pencere(self):
        # Yeni pencere oluştur
        para_yatir_pencere = tk.Toplevel(self.root)
        para_yatir_pencere.title("Para Yatır")
        para_yatir_pencere.geometry("400x500")
        para_yatir_pencere.configure(bg=self.stil['bg'])
        
        # Başlık
        baslik = self.etiket_olustur(para_yatir_pencere, "Para Yatır", self.stil['title_font'])
        baslik.pack(pady=30)

        # Form çerçevesi
        form_frame = tk.Frame(para_yatir_pencere, bg=self.stil['bg'])
        form_frame.pack(pady=20)

        # Miktar
        self.etiket_olustur(form_frame, "Miktar (TL):").pack(pady=5)
        miktar_entry = self.giris_alani_olustur(form_frame)
        miktar_entry.pack(pady=5)

        def para_yatir():
            miktar = miktar_entry.get()
            
            if miktar:
                miktar = float(miktar)
                if self.aktif_hesap.para_yatir(miktar):
                    messagebox.showinfo("Başarılı", f"{miktar} TL yatırıldı.")
                    para_yatir_pencere.destroy()
                else:
                    messagebox.showerror("Hata", "Geçersiz miktar!")
            else:
                messagebox.showerror("Hata", "Lütfen tüm alanları doldurun!")

        # Yatır butonu
        yatir_btn = self.buton_olustur(para_yatir_pencere, "Para Yatır", para_yatir)
        yatir_btn.pack(pady=30)

    def para_cek_pencere(self):
        # Yeni pencere oluştur
        para_cek_pencere = tk.Toplevel(self.root)
        para_cek_pencere.title("Para Çek")
        para_cek_pencere.geometry("400x500")
        para_cek_pencere.configure(bg=self.stil['bg'])
        
        # Başlık
        baslik = self.etiket_olustur(para_cek_pencere, "Para Çek", self.stil['title_font'])
        baslik.pack(pady=30)

        # Form çerçevesi
        form_frame = tk.Frame(para_cek_pencere, bg=self.stil['bg'])
        form_frame.pack(pady=20)

        # Miktar
        self.etiket_olustur(form_frame, "Miktar (TL):").pack(pady=5)
        miktar_entry = self.giris_alani_olustur(form_frame)
        miktar_entry.pack(pady=5)

        def para_cek():
            miktar = miktar_entry.get()
            
            if miktar:
                miktar = float(miktar)
                if self.aktif_hesap.para_cek(miktar):
                    messagebox.showinfo("Başarılı", f"{miktar} TL çekildi.")
                    para_cek_pencere.destroy()
                else:
                    messagebox.showerror("Hata", "Yetersiz bakiye veya geçersiz miktar!")
            else:
                messagebox.showerror("Hata", "Lütfen tüm alanları doldurun!")

        # Çek butonu
        cek_btn = self.buton_olustur(para_cek_pencere, "Para Çek", para_cek)
        cek_btn.pack(pady=30)

    def urun_satin_al_pencere(self):
        # Yeni pencere oluştur
        urun_pencere = tk.Toplevel(self.root)
        urun_pencere.title("Ürün Satın Al")
        urun_pencere.geometry("400x600")
        urun_pencere.configure(bg=self.stil['bg'])
        
        # Scrollbar ve listbox
        scrollbar = tk.Scrollbar(urun_pencere)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        listbox = tk.Listbox(urun_pencere, yscrollcommand=scrollbar.set)
        for urun, fiyat in urunler.items():
            listbox.insert(tk.END, f"{urun} - {fiyat} TL")
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=listbox.yview)
        
        def urun_sec():
            selection = listbox.curselection()
            if selection:
                urun = list(urunler.keys())[selection[0]]
                fiyat = urunler[urun]
                if self.aktif_hesap.urun_satinal(urun, fiyat):
                    messagebox.showinfo("Başarılı", f"{urun} başarıyla satın alındı!")
                    urun_pencere.destroy()
                else:
                    messagebox.showerror("Hata", "Yetersiz bakiye!")

        # Satın al butonu
        satin_al_btn = self.buton_olustur(urun_pencere, "Satın Al", urun_sec)
        satin_al_btn.pack(pady=10)

    def hesap_ozeti_goster(self):
        ozet = self.aktif_hesap.hesap_ozeti()
        messagebox.showinfo("Hesap Özeti", ozet)

    def guncelleme_kontrol(self):
        if surum_kontrol():
            self.root.destroy()
        else:
            # Her 24 saatte bir kontrol et (24 * 60 * 60 * 1000 ms)
            self.root.after(86400000, self.guncelleme_kontrol)

if __name__ == "__main__":
    app = BankaUygulamasi()
    app.root.mainloop()
