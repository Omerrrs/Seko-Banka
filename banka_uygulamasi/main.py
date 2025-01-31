from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.uix.popup import Popup
from kivy.clock import Clock
from veritabani import Veritabani
from android_guncelleme import surum_kontrol
import hashlib

# Renk teması
MAVI = get_color_from_hex('#004B93')
ACIK_MAVI = get_color_from_hex('#0063CC')
BEYAZ = get_color_from_hex('#FFFFFF')

class GirisEkrani(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = Veritabani()
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # Logo veya başlık
        baslik = Label(
            text='Şeko Banka',
            font_size='24sp',
            size_hint_y=None,
            height=100,
            color=BEYAZ
        )
        layout.add_widget(baslik)
        
        # Giriş formu
        self.kullanici = TextInput(
            hint_text='Kullanıcı Adı',
            multiline=False,
            size_hint_y=None,
            height=50,
            background_color=BEYAZ
        )
        layout.add_widget(self.kullanici)
        
        self.sifre = TextInput(
            hint_text='Şifre',
            multiline=False,
            password=True,
            size_hint_y=None,
            height=50,
            background_color=BEYAZ
        )
        layout.add_widget(self.sifre)
        
        # Giriş butonu
        giris_btn = Button(
            text='Giriş Yap',
            size_hint_y=None,
            height=50,
            background_color=ACIK_MAVI,
            background_normal=''
        )
        giris_btn.bind(on_press=self.giris_yap)
        layout.add_widget(giris_btn)
        
        # Kayıt butonu
        kayit_btn = Button(
            text='Hesap Oluştur',
            size_hint_y=None,
            height=50,
            background_color=ACIK_MAVI,
            background_normal=''
        )
        kayit_btn.bind(on_press=self.kayit_ekranina_git)
        layout.add_widget(kayit_btn)
        
        self.add_widget(layout)
    
    def giris_yap(self, instance):
        kullanici = self.kullanici.text
        sifre = self.sifre.text
        
        if kullanici and sifre:
            sifre_hash = hashlib.sha256(sifre.encode()).hexdigest()
            hesap = self.db.hesap_getir(kullanici, sifre_hash)
            
            if hesap:
                app = App.get_running_app()
                app.aktif_hesap = hesap
                self.manager.current = 'ana_ekran'
            else:
                self.hata_goster('Geçersiz kullanıcı adı veya şifre!')
        else:
            self.hata_goster('Lütfen tüm alanları doldurun!')
    
    def kayit_ekranina_git(self, instance):
        self.manager.current = 'kayit_ekrani'
    
    def hata_goster(self, mesaj):
        popup = Popup(
            title='Hata',
            content=Label(text=mesaj),
            size_hint=(None, None),
            size=(300, 200)
        )
        popup.open()

class KayitEkrani(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = Veritabani()
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        baslik = Label(
            text='Yeni Hesap Oluştur',
            font_size='24sp',
            size_hint_y=None,
            height=100,
            color=BEYAZ
        )
        layout.add_widget(baslik)
        
        self.kullanici = TextInput(
            hint_text='Kullanıcı Adı',
            multiline=False,
            size_hint_y=None,
            height=50,
            background_color=BEYAZ
        )
        layout.add_widget(self.kullanici)
        
        self.sifre = TextInput(
            hint_text='Şifre',
            multiline=False,
            password=True,
            size_hint_y=None,
            height=50,
            background_color=BEYAZ
        )
        layout.add_widget(self.sifre)
        
        self.sifre_tekrar = TextInput(
            hint_text='Şifre (Tekrar)',
            multiline=False,
            password=True,
            size_hint_y=None,
            height=50,
            background_color=BEYAZ
        )
        layout.add_widget(self.sifre_tekrar)
        
        kayit_btn = Button(
            text='Hesap Oluştur',
            size_hint_y=None,
            height=50,
            background_color=ACIK_MAVI,
            background_normal=''
        )
        kayit_btn.bind(on_press=self.kayit_ol)
        layout.add_widget(kayit_btn)
        
        geri_btn = Button(
            text='Geri',
            size_hint_y=None,
            height=50,
            background_color=ACIK_MAVI,
            background_normal=''
        )
        geri_btn.bind(on_press=self.geri_don)
        layout.add_widget(geri_btn)
        
        self.add_widget(layout)
    
    def kayit_ol(self, instance):
        kullanici = self.kullanici.text
        sifre = self.sifre.text
        sifre_tekrar = self.sifre_tekrar.text
        
        if kullanici and sifre and sifre_tekrar:
            if sifre == sifre_tekrar:
                sifre_hash = hashlib.sha256(sifre.encode()).hexdigest()
                if self.db.hesap_olustur(kullanici, sifre_hash):
                    self.basari_goster('Hesap başarıyla oluşturuldu!')
                    self.manager.current = 'giris_ekrani'
                else:
                    self.hata_goster('Bu kullanıcı adı zaten kullanılıyor!')
            else:
                self.hata_goster('Şifreler eşleşmiyor!')
        else:
            self.hata_goster('Lütfen tüm alanları doldurun!')
    
    def geri_don(self, instance):
        self.manager.current = 'giris_ekrani'
    
    def hata_goster(self, mesaj):
        popup = Popup(
            title='Hata',
            content=Label(text=mesaj),
            size_hint=(None, None),
            size=(300, 200)
        )
        popup.open()
    
    def basari_goster(self, mesaj):
        popup = Popup(
            title='Başarılı',
            content=Label(text=mesaj),
            size_hint=(None, None),
            size=(300, 200)
        )
        popup.open()

class AnaEkran(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = Veritabani()
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # Üst bilgi alanı
        ust_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=150)
        
        self.hosgeldin_label = Label(
            text='Hoş Geldiniz',
            font_size='24sp',
            color=BEYAZ
        )
        ust_layout.add_widget(self.hosgeldin_label)
        
        self.bakiye_label = Label(
            text='Bakiye: 0.00 TL',
            font_size='20sp',
            color=BEYAZ
        )
        ust_layout.add_widget(self.bakiye_label)
        
        layout.add_widget(ust_layout)
        
        # İşlem butonları
        islemler = [
            ('Para Yatır', self.para_yatir),
            ('Para Çek', self.para_cek),
            ('Para Gönder', self.para_gonder),
            ('Kartlarım', self.kartlarim),
            ('İşlem Geçmişi', self.islem_gecmisi),
            ('Çıkış Yap', self.cikis_yap)
        ]
        
        for islem in islemler:
            btn = Button(
                text=islem[0],
                size_hint_y=None,
                height=50,
                background_color=ACIK_MAVI,
                background_normal=''
            )
            btn.bind(on_press=islem[1])
            layout.add_widget(btn)
        
        self.add_widget(layout)
    
    def on_pre_enter(self):
        app = App.get_running_app()
        self.hosgeldin_label.text = f"Hoş Geldiniz, {app.aktif_hesap['hesap_sahibi']}"
        self.bakiye_label.text = f"Bakiye: {app.aktif_hesap['bakiye']:.2f} TL"
    
    def para_yatir(self, instance):
        self.manager.current = 'para_yatir_ekrani'
    
    def para_cek(self, instance):
        self.manager.current = 'para_cek_ekrani'
    
    def para_gonder(self, instance):
        self.manager.current = 'para_gonder_ekrani'
    
    def kartlarim(self, instance):
        self.manager.current = 'kartlar_ekrani'
    
    def islem_gecmisi(self, instance):
        self.manager.current = 'islem_gecmisi_ekrani'
    
    def cikis_yap(self, instance):
        app = App.get_running_app()
        app.aktif_hesap = None
        self.manager.current = 'giris_ekrani'

class BankaApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.aktif_hesap = None
    
    def build(self):
        # Ekran yöneticisi
        sm = ScreenManager()
        
        # Ekranları ekle
        sm.add_widget(GirisEkrani(name='giris_ekrani'))
        sm.add_widget(KayitEkrani(name='kayit_ekrani'))
        sm.add_widget(AnaEkran(name='ana_ekran'))
        
        # Arka plan rengi
        Window.clearcolor = MAVI
        
        # Güncelleme kontrolü (1 saniye sonra)
        Clock.schedule_once(lambda dt: surum_kontrol(), 1)
        
        return sm

if __name__ == '__main__':
    BankaApp().run()
