import sqlite3
import hashlib
import json
from datetime import datetime

class Veritabani:
    def __init__(self):
        self.conn = sqlite3.connect('banka.db')
        self.cursor = self.conn.cursor()
        self.tablolari_olustur()
    
    def tablolari_olustur(self):
        # Hesaplar tablosu
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS hesaplar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hesap_sahibi TEXT UNIQUE NOT NULL,
            sifre_hash TEXT NOT NULL,
            bakiye REAL DEFAULT 0,
            donduruldu INTEGER DEFAULT 0,
            yas INTEGER DEFAULT 0,
            cinsiyet TEXT DEFAULT '',
            olusturma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # İşlem geçmişi tablosu
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS islem_gecmisi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hesap_id INTEGER,
            islem_tipi TEXT NOT NULL,
            miktar REAL,
            aciklama TEXT,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hesap_id) REFERENCES hesaplar (id)
        )
        ''')

        # Kartlar tablosu
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS kartlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hesap_id INTEGER,
            kart_turu TEXT NOT NULL,
            kart_numarasi TEXT UNIQUE NOT NULL,
            son_kullanim_tarihi TEXT NOT NULL,
            cvv TEXT NOT NULL,
            limit REAL DEFAULT 0,
            aktif INTEGER DEFAULT 1,
            olusturma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hesap_id) REFERENCES hesaplar (id)
        )
        ''')

        self.conn.commit()
    
    def hesap_olustur(self, hesap_sahibi, sifre):
        try:
            sifre_hash = hashlib.sha256(sifre.encode()).hexdigest()
            self.cursor.execute('''
            INSERT INTO hesaplar (hesap_sahibi, sifre_hash)
            VALUES (?, ?)
            ''', (hesap_sahibi, sifre_hash))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def hesap_getir(self, hesap_sahibi, sifre):
        sifre_hash = hashlib.sha256(sifre.encode()).hexdigest()
        self.cursor.execute('''
        SELECT * FROM hesaplar 
        WHERE hesap_sahibi = ? AND sifre_hash = ?
        ''', (hesap_sahibi, sifre_hash))
        return self.cursor.fetchone()
    
    def bakiye_guncelle(self, hesap_id, yeni_bakiye):
        self.cursor.execute('''
        UPDATE hesaplar 
        SET bakiye = ? 
        WHERE id = ?
        ''', (yeni_bakiye, hesap_id))
        self.conn.commit()
    
    def islem_ekle(self, hesap_id, islem_tipi, miktar, aciklama):
        self.cursor.execute('''
        INSERT INTO islem_gecmisi (hesap_id, islem_tipi, miktar, aciklama)
        VALUES (?, ?, ?, ?)
        ''', (hesap_id, islem_tipi, miktar, aciklama))
        self.conn.commit()
    
    def islem_gecmisi_getir(self, hesap_id):
        self.cursor.execute('''
        SELECT islem_tipi, miktar, aciklama, tarih 
        FROM islem_gecmisi 
        WHERE hesap_id = ?
        ORDER BY tarih DESC
        ''', (hesap_id,))
        return self.cursor.fetchall()
    
    def sifre_guncelle(self, hesap_id, yeni_sifre):
        sifre_hash = hashlib.sha256(yeni_sifre.encode()).hexdigest()
        self.cursor.execute('''
        UPDATE hesaplar 
        SET sifre_hash = ? 
        WHERE id = ?
        ''', (sifre_hash, hesap_id))
        self.conn.commit()
    
    def hesap_bilgileri_guncelle(self, hesap_id, yas=None, cinsiyet=None):
        if yas is not None:
            self.cursor.execute('''
            UPDATE hesaplar 
            SET yas = ? 
            WHERE id = ?
            ''', (yas, hesap_id))
        
        if cinsiyet is not None:
            self.cursor.execute('''
            UPDATE hesaplar 
            SET cinsiyet = ? 
            WHERE id = ?
            ''', (cinsiyet, hesap_id))
        
        self.conn.commit()
    
    def hesap_dondur(self, hesap_id, durum):
        self.cursor.execute('''
        UPDATE hesaplar 
        SET donduruldu = ? 
        WHERE id = ?
        ''', (1 if durum else 0, hesap_id))
        self.conn.commit()
    
    def hesap_var_mi(self, hesap_sahibi):
        self.cursor.execute('''
        SELECT COUNT(*) FROM hesaplar 
        WHERE hesap_sahibi = ?
        ''', (hesap_sahibi,))
        return self.cursor.fetchone()[0] > 0
    
    def kart_olustur(self, hesap_id, kart_turu, limit=0):
        import random
        from datetime import datetime, timedelta

        # Rastgele 16 haneli kart numarası oluştur
        while True:
            kart_numarasi = ''.join([str(random.randint(0, 9)) for _ in range(16)])
            try:
                # Benzersiz kart numarası kontrolü
                self.cursor.execute('SELECT id FROM kartlar WHERE kart_numarasi = ?', (kart_numarasi,))
                if not self.cursor.fetchone():
                    break
            except:
                continue

        # Son kullanım tarihi (3 yıl sonrası)
        son_kullanim = (datetime.now() + timedelta(days=3*365)).strftime('%m/%y')
        
        # CVV kodu
        cvv = ''.join([str(random.randint(0, 9)) for _ in range(3)])

        try:
            self.cursor.execute('''
            INSERT INTO kartlar (hesap_id, kart_turu, kart_numarasi, son_kullanim_tarihi, cvv, limit)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (hesap_id, kart_turu, kart_numarasi, son_kullanim, cvv, limit))
            self.conn.commit()
            return True
        except:
            return False

    def kartlari_getir(self, hesap_id):
        self.cursor.execute('''
        SELECT kart_turu, kart_numarasi, son_kullanim_tarihi, limit, aktif
        FROM kartlar 
        WHERE hesap_id = ?
        ORDER BY olusturma_tarihi DESC
        ''', (hesap_id,))
        return self.cursor.fetchall()

    def kart_sil(self, kart_numarasi, hesap_id):
        try:
            self.cursor.execute('''
            DELETE FROM kartlar 
            WHERE kart_numarasi = ? AND hesap_id = ?
            ''', (kart_numarasi, hesap_id))
            self.conn.commit()
            return True
        except:
            return False

    def kart_guncelle(self, kart_numarasi, hesap_id, yeni_limit=None, aktif=None):
        try:
            if yeni_limit is not None:
                self.cursor.execute('''
                UPDATE kartlar 
                SET limit = ? 
                WHERE kart_numarasi = ? AND hesap_id = ?
                ''', (yeni_limit, kart_numarasi, hesap_id))
            
            if aktif is not None:
                self.cursor.execute('''
                UPDATE kartlar 
                SET aktif = ? 
                WHERE kart_numarasi = ? AND hesap_id = ?
                ''', (1 if aktif else 0, kart_numarasi, hesap_id))
            
            self.conn.commit()
            return True
        except:
            return False

    def __del__(self):
        self.conn.close()
