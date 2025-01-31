[app]

# Uygulama adı
title = Şeko Banka

# Paket adı
package.name = sekobanka

# Paket domain'i
package.domain = com.sekobanka

# Kaynak dosya
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,json
source.include_patterns = assets/*,images/*
source.exclude_dirs = tests, bin, venv

# Versiyon bilgisi
version = 1.0.0

# Gereksinimler
requirements = python3,kivy,sqlite3,requests

# Android izinleri
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE

# Simge ve başlangıç resmi
#android.presplash.filename = %(source.dir)s/data/presplash.png
#android.icon.filename = %(source.dir)s/data/icon.png

# Android API seviyesi
android.api = 31

# NDK versiyonu
android.ndk = 23b

# SDK versiyonu
android.sdk = 31

# Minimum SDK versiyonu
android.minapi = 21

# NDK versiyonu
android.ndk_api = 21

# Uygulama ayarları
orientation = portrait
fullscreen = 0
android.arch = arm64-v8a

# Buildozer ayarları
log_level = 2
