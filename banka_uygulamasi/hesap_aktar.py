import json
from veritabani import Veritabani
import hashlib

def json_hesaplari_aktar():
    try:
        # JSON dosyasını oku
        with open("hesaplar.json", "r") as dosya:
            hesaplar = json.load(dosya)
            
        # Veritabanı bağlantısı
        db = Veritabani()
        
        # Her hesabı veritabanına aktar
        for hesap in hesaplar:
            # Hesap bilgilerini al
            hesap_sahibi = hesap['hesap_sahibi']
            sifre_hash = hesap['sifre_hash']  # Zaten hash'lenmiş
            bakiye = hesap.get('bakiye', 0)
            yas = hesap.get('yas', 0)
            cinsiyet = hesap.get('cinsiyet', '')
            donduruldu = 1 if hesap.get('donduruldu', False) else 0
            
            # Hesabı veritabanına ekle
            db.cursor.execute('''
            INSERT INTO hesaplar (hesap_sahibi, sifre_hash, bakiye, yas, cinsiyet, donduruldu)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (hesap_sahibi, sifre_hash, bakiye, yas, cinsiyet, donduruldu))
            
            # Yeni eklenen hesabın ID'sini al
            hesap_id = db.cursor.lastrowid
            
            # İşlem geçmişini aktar
            for hareket in hesap.get('hareket_gecmisi', []):
                # İşlem tipini ve miktarı belirle
                if "yatırıldı" in hareket:
                    islem_tipi = "para_yatirma"
                    miktar = float(hareket.split()[0])
                elif "çekildi" in hareket:
                    islem_tipi = "para_cekme"
                    miktar = -float(hareket.split()[0])
                elif "satın alındı" in hareket:
                    islem_tipi = "alisveris"
                    miktar = -float(hareket.split()[-2])
                else:
                    islem_tipi = "diger"
                    miktar = 0
                
                # İşlemi veritabanına ekle
                db.cursor.execute('''
                INSERT INTO islem_gecmisi (hesap_id, islem_tipi, miktar, aciklama)
                VALUES (?, ?, ?, ?)
                ''', (hesap_id, islem_tipi, miktar, hareket))
        
        # Değişiklikleri kaydet
        db.conn.commit()
        print("Hesaplar başarıyla aktarıldı!")
        
    except FileNotFoundError:
        print("hesaplar.json dosyası bulunamadı.")
    except Exception as e:
        print(f"Hata oluştu: {e}")

if __name__ == "__main__":
    json_hesaplari_aktar()
