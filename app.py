import streamlit as st
import requests
from xml.etree.ElementTree import fromstring
from datetime import datetime
import pandas as pd
import sqlite3

st.set_page_config(page_title="FiyatOpt Kimya", page_icon="📦", layout="wide")

# ====================== TÜRKİYE İLLERİ ======================
iller = ["Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya", "Ankara", "Antalya", "Ardahan", "Artvin", 
         "Aydın", "Balıkesir", "Bartın", "Batman", "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", 
         "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Düzce", "Edirne", "Elazığ", "Erzincan", "Erzurum", 
         "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Iğdır", "Isparta", "İstanbul", "İzmir", 
         "Kahramanmaraş", "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri", "Kırıkkale", "Kırklareli", "Kırşehir", 
         "Kilis", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Mardin", "Mersin", "Muğla", "Muş", "Nevşehir", 
         "Niğde", "Ordu", "Osmaniye", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Şanlıurfa", "Şırnak", 
         "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Uşak", "Van", "Yalova", "Yozgat", "Zonguldak"]

# ====================== VERİTABANI ======================
DB_FILE = "fiyatopt.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS urunler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Urun_Adi TEXT NOT NULL,
        Fabrika TEXT NOT NULL,
        Fabrika_Kodu INTEGER NOT NULL,
        Kategori TEXT NOT NULL,
        Maliyet_TL_kg REAL NOT NULL,
        Nakliye_TL_kg REAL NOT NULL
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS nakliye (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Fabrika TEXT NOT NULL,
        Sevk_Ili TEXT NOT NULL,
        Sevk_Ilce TEXT,
        Nakliye_TL_kg REAL NOT NULL
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS kayitlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Tarih TEXT, Urun TEXT, Fabrika_Kodu INTEGER, Musteri TEXT, Fabrika TEXT,
        Maliyet_TL_kg REAL, Satis_TL_kg REAL, Kar_TL_kg REAL
    )''')
    conn.commit()
    conn.close()

init_db()

# ====================== TCMB KURLARI ======================
def tcmb_kur_getir():
    try:
        xml = requests.get("https://www.tcmb.gov.tr/kurlar/today.xml", timeout=15).text
        root = fromstring(xml)
        tarih = root.find(".//Tarih").attrib.get("Tarih", datetime.now().strftime("%d.%m.%Y"))
        rates = {curr.get("Kod"): float(curr.find("ForexSelling").text) 
                 for curr in root.findall(".//Currency") if curr.find("ForexSelling") is not None}
        st.success(f"✅ TCMB Kurları Güncellendi: {tarih}")
        return rates
    except:
        st.error("❌ TCMB kurları alınamadı. Örnek kurlar kullanılıyor.")
        return {"USD": 34.50, "EUR": 37.80, "GBP": 44.20, "CHF": 39.20}

rates = tcmb_kur_getir()

# ====================== SIDEBAR ======================
st.sidebar.title("FiyatOpt Kimya")
sayfa = st.sidebar.radio("Menü", ["Hesaplama", "Ürün Yönetimi", "Nakliye Yönetimi", "Geçmiş Kayıtlar"])
st.sidebar.info(f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}")

# ====================== ÜRÜN YÖNETİMİ ======================
if sayfa == "Ürün Yönetimi":
    st.header("🗃️ Ürün Yönetimi")

    with st.expander("➕ Yeni Ürün Ekle", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            urun_adi = st.text_input("Ürün Adı")
            kategori = st.selectbox("Kategori", ["Lignosülfonat - Ligno Esaslı", "Sülfonat Naftalin - Naftalin Esaslı", "Polikarboksilat Eter - PCE Esaslı"])
        with col2:
            fabrika = st.selectbox("Fabrika", ["Gebze", "Adana", "Trabzon"])
            fab_kodu = {"Gebze": 14, "Adana": 16, "Trabzon": 15}[fabrika]
            maliyet = st.number_input("Maliyet (TL/kg)", min_value=0.0, step=0.01)
            nakliye = st.number_input("Varsayılan Nakliye (TL/kg)", min_value=0.0, step=0.01)
        
        if st.button("Ürünü Kaydet", type="primary"):
            if urun_adi:
                conn = get_db()
                conn.execute("INSERT INTO urunler (Urun_Adi, Fabrika, Fabrika_Kodu, Kategori, Maliyet_TL_kg, Nakliye_TL_kg) VALUES (?,?,?,?,?,?)",
                             (urun_adi, fabrika, fab_kodu, kategori, maliyet, nakliye))
                conn.commit()
                conn.close()
                st.success(f"✅ {urun_adi} kaydedildi!")
                st.rerun()

    st.subheader("Mevcut Ürünler")
    df = pd.read_sql_query("SELECT * FROM urunler", get_db())
    st.dataframe(df, use_container_width=True)

# ====================== NAKLİYE YÖNETİMİ ======================
elif sayfa == "Nakliye Yönetimi":
    st.header("🚛 Nakliye Yönetimi")

    col1, col2 = st.columns(2)
    with col1:
        fabrika = st.selectbox("Fabrika", ["Gebze", "Adana", "Trabzon"])
    with col2:
        sevk_ili = st.selectbox("Sevk İli", iller)
    sevk_ilce = st.text_input("Sevk İlçe (Opsiyonel)")

    ucret = st.number_input("Nakliye Ücreti (TL/kg)", min_value=0.0, step=0.01, value=12.5)

    if st.button("Nakliye Tarifesini Kaydet", type="primary"):
        conn = get_db()
        conn.execute("INSERT OR REPLACE INTO nakliye (Fabrika, Sevk_Ili, Sevk_Ilce, Nakliye_TL_kg) VALUES (?,?,?,?)",
                     (fabrika, sevk_ili, sevk_ilce or "", ucret))
        conn.commit()
        conn.close()
        st.success(f"✅ {fabrika} → {sevk_ili} kaydedildi!")

    st.subheader("Mevcut Nakliye Tarifeleri")
    st.dataframe(pd.read_sql_query("SELECT * FROM nakliye", get_db()), use_container_width=True)

# ====================== HESAPLAMA ======================
elif sayfa == "Hesaplama":
    st.header("🧪 Birim Fiyat Hesaplama")

    urunler = pd.read_sql_query("SELECT * FROM urunler", get_db())
    if urunler.empty:
        st.warning("Önce Ürün Yönetimi’nden ürün ekleyin!")
        st.stop()

    urunler["Gosterim"] = urunler["Urun_Adi"] + " (" + urunler["Fabrika"] + " - Kod: " + urunler["Fabrika_Kodu"].astype(str) + ")"
    secilen = st.selectbox("Ürün Seç", urunler["Gosterim"])
    urun = urunler[urunler["Gosterim"] == secilen].iloc[0]

    sevk_ili = st.selectbox("Sevk İli", iller)

    # NAKLİYE OTOMATİK ÇEKME
    nakliye_df = pd.read_sql_query("SELECT Nakliye_TL_kg FROM nakliye WHERE Fabrika=? AND Sevk_Ili=?", 
                                   get_db(), params=(urun["Fabrika"], sevk_ili))
    default_nak = float(nakliye_df.iloc[0]["Nakliye_TL_kg"]) if not nakliye_df.empty else 8.0

    maliyet = st.number_input("Maliyet (TL/kg)", value=float(urun["Maliyet_TL_kg"]), step=0.01)
    nakliye = st.number_input("Nakliye (TL/kg)", value=default_nak, step=0.01)
    marj = st.number_input("Marj (%)", value=25.0, step=0.1)

    musteri_tipi = st.selectbox("Müşteri Tipi", ["Direkt Satış Müşterisi", "Bayi"])
    musteri_adi = st.text_input("Müşteri Adı", "ABC İnşaat")

    if st.button("Hesapla ve Kaydet", type="primary"):
        bm = maliyet + nakliye
        bs = bm * (1 + marj / 100)
        bk = bs - bm
        st.success("✅ Hesaplandı!")
        st.write(f"**{urun['Urun_Adi']}** → {sevk_ili}")
        st.write(f"Birim Maliyet: **{bm:.2f} TL** | Satış: **{bs:.2f} TL** | Kâr: **{bk:.2f} TL**")

st.caption("FiyatOpt Kimya • Nakliye Otomatik Çekme Aktif")
